"""Small-angle neutron scattering (SANS) technique family.

P4 ships this package incrementally. P4.1 adds only the data-model skeleton
under :mod:`exphub.techniques.sans.models` (sample info, strategy table, I(Q)
reduction placeholder). The technique *manifest* — which is what
``get_technique("sans")`` discovers via the import side effect — lands in a
later P4 step, together with view-models, views, agent phases and prompts.

Until the manifest exists, importing this package is a cheap no-op; it does
**not** register a technique. ``get_technique("sans")`` therefore still raises
``KeyError`` (no manifest registered) by design at this point in the refactor.
"""
