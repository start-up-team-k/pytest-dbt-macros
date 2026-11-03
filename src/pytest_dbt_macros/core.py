"""Render dbt macros with plain Jinja: no dbt-core, no adapter, no profiles.yml, no database."""
import datetime
import functools
import itertools
import os
import re
from pathlib import Path
from types import SimpleNamespace

import jinja2
import sqlglot
import yaml
from jinja2 import nodes
from jinja2.ext import Extension
from sqlglot.optimizer.normalize_identifiers import normalize_identifiers

VENDORED = Path(__file__).parent / "vendored"  # dbt's cross-database macros (Apache-2.0), see NOTICE
_MISSING = object()


class CompilationError(Exception):
    """Raised by `exceptions.raise_compiler_error` and by unsupported stubs."""


class _Return(Exception):
    def __init__(self, value):
        self.value = value


class _SkipBlocks(Extension):
    """dbt-only block tags (`{% test %}` etc.) are parsed and dropped, so files containing them load."""

    tags = {"test", "materialization", "snapshot"}

    def parse(self, parser):
        tag = next(parser.stream).value
        while parser.stream.current.type != "block_end":
            next(parser.stream)
        parser.parse_statements((f"name:end{tag}",), drop_needle=True)
        return nodes.Output([])


_ENV = jinja2.Environment(extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols", _SkipBlocks])


@functools.lru_cache(maxsize=None)
def _parse(path, text):
    """Parse a file once per process; returns {macro name: AST of that macro alone}.

    Like dbt, every macro becomes its own template, so sibling calls go through the namespace
    (and therefore through `return` handling) instead of Jinja's file-local variables."""
    ast = _ENV.parse(text, filename=path)
    return {n.name: nodes.Template([n], lineno=n.lineno) for n in ast.body if isinstance(n, nodes.Macro)}


@functools.lru_cache(maxsize=None)
def _compile(path, name, text):
    return _ENV.template_class.from_code(_ENV, _ENV.compile(_parse(path, text)[name], filename=path), _ENV.globals)


class Relation(str):
    """What `ref()`/`source()` return: renders as the bare name (like SQLFluff's mock), not a quoted path."""

    def __new__(cls, identifier, schema=None, database=None):
        self = super().__new__(cls, identifier)
        self.identifier, self.schema, self.database = identifier, schema, database
        return self


class _Namespace:
    """`dbt_utils.star(...)`: attribute access on a package name."""

    def __init__(self, project, package):
        self._p, self._pkg = project, package

    def __getattr__(self, name):
        if name.startswith("__") or name not in self._p._macros.get(self._pkg, {}):
            raise AttributeError(f"package '{self._pkg}' has no macro '{name}'")
        return functools.partial(self._p._call, self._pkg, name)


class _Adapter:
    """The `adapter` context object. Only what rendering needs; everything else needs a database."""

    def __init__(self, project, package):
        self._p, self._pkg = project, package

    def type(self):
        return self._p.target["type"]

    def quote(self, identifier):
        q = "`" if self.type() == "bigquery" else '"'
        return f"{q}{identifier}{q}"

    def __getattr__(self, name):
        raise CompilationError(f"adapter.{name} needs a database connection; pytest-dbt-macros has none")

    def dispatch(self, macro_name, macro_namespace=None, packages=None):
        # Mirrors dbt-core's ProviderContext.dispatch.
        p = self._p
        if "." in macro_name:
            raise CompilationError(f'In adapter.dispatch, got a macro name of "{macro_name}", but "." is not valid')
        if packages is not None:
            raise CompilationError("adapter.dispatch(packages=...) was removed; use macro_namespace")
        search = [None]
        if macro_namespace is not None:
            order = next((d["search_order"] for d in p.dispatch if d.get("macro_namespace") == macro_namespace), None)
            if order:
                search = order
            elif macro_namespace in p.dependencies:
                search = [p.root, macro_namespace]
        t = p.target["type"]
        tried = []
        for package in search:
            for prefix in [t, *p.parents.get(t, []), "default"]:
                name = f"{prefix}__{macro_name}"
                tried.append(f"{package}.{name}" if package else name)
                if found := p._lookup(self._pkg, package, name):
                    return found
        raise CompilationError(
            f"In dispatch: No macro named '{macro_name}' found within namespace: '{macro_namespace}'\n"
            f"    Searched for: {', '.join(map(repr, tried))}"
        )


class _Config:
    def __call__(self, *args, **kwargs):
        return ""

    def get(self, key, default=None):
        return default

    def require(self, key):
        raise CompilationError(f"config.require('{key}'): model config is not available in macro tests")


class MacroProject:
    """A dbt project's macros, callable from Python.

    >>> p = MacroProject("path/to/dbt/project", target="snowflake")
    >>> p.dbt_utils.generate_surrogate_key(["a", "b"])   # package namespace
    >>> p.my_macro(1, 2)                                 # macro of the project itself
    >>> p.render("{{ my_macro(1) }}")                    # any Jinja, in the project's context
    Change `p.target["type"]`, `p.vars`, `p.env` at any time; macros read them at call time.
    """

    def __init__(self, project_dir=".", target="postgres", vars=None, env=None):
        self.target = {"type": target, "name": "test", "schema": "public", "database": "db", "threads": 1}
        self.env = dict(env or {})  # overrides os.environ for env_var()
        self.parents = {"redshift": ["postgres"]}  # adapter -> parent adapters for dispatch
        self.logs = []  # messages from log() / exceptions.warn()
        self._macros = {}  # package -> {macro name: [(path, name, text), jinja macro once loaded]}
        self._ctx_cache = {}
        project_dir = Path(project_dir)
        for f in sorted(VENDORED.rglob("*.sql")):
            self._add("dbt", f)
        cfg = self._add_project(project_dir)
        self.root = cfg["name"]
        self.dispatch = cfg.get("dispatch") or []
        pv = cfg.get("vars") or {}
        self.vars = {**{k: v for k, v in pv.items() if k != self.root}, **(pv.get(self.root) or {}), **(vars or {})}
        self.dependencies = set()
        for d in sorted((project_dir / cfg.get("packages-install-path", "dbt_packages")).glob("*/dbt_project.yml")):
            self.dependencies.add(self._add_project(d.parent)["name"])
        self._stubs = self._make_stubs()

    # -- loading -----------------------------------------------------------------------------
    def _add(self, package, path):
        text = path.read_text()
        for name in _parse(str(path), text):
            self._macros.setdefault(package, {})[name] = [(str(path), name, text), None]  # [source, loaded macro]

    def _add_project(self, path):
        cfg = yaml.safe_load((path / "dbt_project.yml").read_text()) if (path / "dbt_project.yml").exists() else {}
        cfg.setdefault("name", "project")
        for rel in cfg.get("macro-paths", ["macros"]):
            for f in sorted((path / rel).rglob("*.sql")):
                self._add(cfg["name"], f)
        return cfg

    # -- the Jinja context dbt macros see ------------------------------------------------------
    def _make_stubs(self):
        def var(name, default=_MISSING):
            if name in self.vars:
                return self.vars[name]
            if default is _MISSING:
                raise CompilationError(f"Required var '{name}' not found; pass vars={{'{name}': ...}} to MacroProject")
            return default

        def env_var(name, default=_MISSING):
            value = {**os.environ, **self.env}.get(name, default)
            if value is _MISSING:
                raise CompilationError(f"Env var required but not provided: '{name}'")
            return value

        def ref(*args, **kwargs):
            return Relation(args[-1], self.target["schema"], self.target["database"])

        def source(source_name, table_name):
            return Relation(f"{source_name}.{table_name}", self.target["schema"], self.target["database"])

        def return_(value):
            raise _Return(value)

        def log(msg, info=False):
            self.logs.append(str(msg))
            return ""

        def needs_db(name):
            def fail(*args, **kwargs):
                raise CompilationError(f"{name} needs a database connection; pytest-dbt-macros has none")

            return fail

        def raise_compiler_error(msg, node=None):
            raise CompilationError(str(msg))

        exceptions = SimpleNamespace(
            raise_compiler_error=raise_compiler_error,
            raise_not_implemented=raise_compiler_error,
            warn=lambda msg, node=None: self.logs.append(str(msg)) or "",
        )
        return dict(
            var=var, env_var=env_var, ref=ref, source=source, log=log, exceptions=exceptions,
            **{n: needs_db(n) for n in ('run_query', 'statement', 'load_result')},
            target=self.target, config=_Config(), execute=True, api=SimpleNamespace(Column=self._column_api()),
            dbt_version="1.12.6",  # the version the baselines were compiled with
            modules=SimpleNamespace(datetime=datetime, re=re, itertools=itertools),
            **{"return": return_},
        )

    def _column_api(self):
        """api.Column.translate_type / numeric_type, as in dbt-adapters' Column (BigQuery differs, the rest share it)."""
        bigquery = lambda: self.target["type"] == "bigquery"  # noqa: E731

        def translate_type(dtype):
            labels = {"TEXT": "STRING", "FLOAT": "FLOAT64", "INTEGER": "INT64"} if bigquery() else {"STRING": "TEXT"}
            return labels.get(dtype.upper(), dtype)

        def numeric_type(dtype, precision, scale):
            return dtype if bigquery() or precision is None or scale is None else f"{dtype}({precision},{scale})"

        return SimpleNamespace(translate_type=translate_type, numeric_type=numeric_type)

    def _context(self, package):
        """Names visible inside `package`'s macros, lowest to highest priority (same order as dbt)."""
        if package not in self._ctx_cache:
            ctx = dict(self._stubs, adapter=_Adapter(self, package))
            ctx.update(self._flat("dbt"))  # dbt's own macros are callable bare, too
            ctx.update({pkg: _Namespace(self, pkg) for pkg in self._macros})
            ctx.update(self._flat(self.root))
            ctx.update(self._flat(package))
            self._ctx_cache[package] = ctx
        return self._ctx_cache[package]

    def _flat(self, package):
        return {n: functools.partial(self._call, package, n) for n in self._macros.get(package, {})}

    def _lookup(self, from_package, package, name):
        """dispatch lookup: a named package, or (None) the calling package, then the root project, then dbt."""
        for pkg in [package] if package else [from_package, self.root, "dbt"]:
            if name in self._macros.get(pkg, {}):
                return functools.partial(self._call, pkg, name)

    def _call(self, package, name, *args, **kwargs):
        entry = self._macros[package][name]
        if entry[1] is None:  # define the macro once, in this package's context
            template = _compile(*entry[0])
            context = template.new_context(self._context(package))
            for _ in template.root_render_func(context):
                pass
            entry[1] = context.vars[name]
        try:
            return str(entry[1](*args, **kwargs))
        except _Return as r:
            return r.value

    # -- public API ----------------------------------------------------------------------------
    def render(self, source, **context):
        """Render a Jinja string as if it were a model body, in the root project's context."""
        return _ENV.from_string(source).render({**self._context(self.root), **context})

    def __getattr__(self, name):
        if name.startswith("_") or "_macros" not in self.__dict__:
            raise AttributeError(name)
        if name in self._macros:
            return _Namespace(self, name)
        if name in self._macros.get(self.root, {}):
            return functools.partial(self._call, self.root, name)
        raise AttributeError(f"no package or root macro named '{name}'")


def _normalize(sql, dialect):
    try:
        return ";\n".join(normalize_identifiers(t, dialect).sql(dialect=dialect) for t in sqlglot.parse(sql, read=dialect) if t)
    except sqlglot.errors.SqlglotError:  # not parseable (e.g. a bare column list): compare whitespace-insensitively
        return " ".join(sql.split())


def assert_sql_equal(actual, expected, dialect=None):
    """Assert two SQL strings are equal after sqlglot normalization (whitespace, keyword case, identifier case)."""
    a, b = _normalize(actual, dialect), _normalize(expected, dialect)
    assert a == b, f"SQL differs ({dialect or 'generic'}):\n  actual:   {a}\n  expected: {b}"
