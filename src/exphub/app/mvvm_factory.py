"""Module for the factory that creates viewmodels used in the application."""

from nova.mvvm.interface import BindingInterface

from ..agent.bridge import bridged_submodels

# The composition root wires the technique-specific steering VM into the
# app shell. This direct import is the transitional seam; P3 makes the
# steering VM manifest-supplied (TechniqueManifest.root_model_factory).
from ..techniques.single_crystal.view_models.steering import SingleCrystalSteeringViewModel
from .models.chat import ChatModel
from .models.main_model import MainModel
from .view_models.app_shell import AppShellViewModel
from .view_models.chat import ChatViewModel


def create_viewmodels(binding: BindingInterface) -> dict:
    model = MainModel()
    vm: dict = {}
    # The technique-agnostic shell owns tab navigation, the beamline
    # selector and the global snackbar; the steering VM owns the
    # single-crystal tabs and reuses the shell snackbar via ``notify``.
    shell_vm = AppShellViewModel(binding)
    steering_vm = SingleCrystalSteeringViewModel(model, binding, notify_fn=shell_vm.notify)
    vm["app_shell"] = shell_vm
    vm["steering"] = steering_vm

    # Chat / Agent viewmodel — shares the same MainModel so the agent
    # can read and write the same Pydantic fields the left-side tabs use.
    # Sub-model binds + action verbs resolve against the steering VM;
    # tab navigation resolves against the shell VM.
    chat_model = ChatModel()
    main_bindings = {name: getattr(steering_vm, f"{name}_bind") for name in bridged_submodels()}
    vm["chat"] = ChatViewModel(
        chat_model, model, binding, main_bindings,
        nav_fn=shell_vm.navigate_to_tab,
        main_vm=steering_vm,
    )

    return vm
