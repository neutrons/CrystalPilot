# Layer: app (`exphub.app`)

The trame application shell and MVVM wiring. It is **technique-agnostic**: it
renders whatever the active technique manifest and beamline spec declare, and
never names a single-crystal or SANS class.

## What lives here

```
app/
├── main.py, __main__.py     MainApp entry point + server bootstrap
├── mvvm_factory.py          create_viewmodels(): builds the VM graph
├── models/
│   ├── main_model.py        single-crystal fallback composite root
│   └── chat.py              chat model
├── view_models/
│   ├── app_shell.py         AppShellViewModel: tab nav, selector, snackbar
│   └── chat.py              ChatViewModel: bridges agent <-> technique model
└── views/
    ├── main_view.py, tabs_panel.py, chat_pane.py   shell chrome
    ├── tab_content_panel.py  manifest-driven 5-slot tab dispatcher
    └── placeholder_tab.py     fall-through tab (message + links)
```

## How it wires a technique

```
create_viewmodels():
   root  = active_technique().root_model_factory()   (or MainModel fallback)
   shell = AppShellViewModel(binding)                 (nav/selector/snackbar)
   steer = active_technique().steering_vm_factory(root, ...)  (tab *_bind owner)
   chat  = ChatViewModel(.., binds from bridged_submodels(), main_vm=steer)
```

The **TabContentPanel** resolves each of the five `TabKey` slots uniformly:
beamline override -> technique default -> opted-in optional default ->
placeholder. No technique vocabulary appears in the dispatcher.

## Rule of thumb

The shell owns *navigation and composition*; the technique steering VM owns the
*tab content state*. Cross-technique beamline switches are restart-gated in v1.
See [architecture/techniques.md](techniques.md) for the VM/manifest seam.
