"""Module for the factory that creates viewmodels used in the application."""

from nova.mvvm.interface import BindingInterface

from ..agent.bridge import bridged_submodels
from .models.chat import ChatModel
from .models.main_model import MainModel
from .view_models.chat import ChatViewModel
from .view_models.main import MainViewModel


def create_viewmodels(binding: BindingInterface) -> dict:
    model = MainModel()
    vm: dict = {}
    main_vm = MainViewModel(model, binding)
    vm["main"] = main_vm

    # Chat / Agent viewmodel — shares the same MainModel so the agent
    # can read and write the same Pydantic fields the left-side tabs use.
    chat_model = ChatModel()
    main_bindings = {name: getattr(main_vm, f"{name}_bind") for name in bridged_submodels()}
    vm["chat"] = ChatViewModel(
        chat_model, model, binding, main_bindings,
        nav_fn=main_vm.navigate_to_tab,
        main_vm=main_vm,
    )

    return vm
