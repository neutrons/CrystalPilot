"""Automated tests for data tables."""

from typing import Any

from trame.app import get_server
from trame.ui.vuetify3 import SinglePageLayout
from trame.widgets import html
from trame.widgets import vuetify3 as vuetify

server = get_server(client_type="vue3")
state = server.state

# Default record
DEFAULT_RECORD = {
    "title": "",
    "author": "",
    "genre": "",
    "year": 2023,
    "pages": 1,
}

# State variables
state.books = [
    {"id": 1, "title": "To Kill a Mockingbird", "author": "Harper Lee", "genre": "Fiction", "year": 1960, "pages": 281},
    {"id": 2, "title": "1984", "author": "George Orwell", "genre": "Dystopian", "year": 1949, "pages": 328},
    {
        "id": 3,
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "genre": "Fiction",
        "year": 1925,
        "pages": 180,
    },
    {"id": 4, "title": "Sapiens", "author": "Yuval Noah Harari", "genre": "Non-Fiction", "year": 2011, "pages": 443},
    {"id": 5, "title": "Dune", "author": "Frank Herbert", "genre": "Sci-Fi", "year": 1965, "pages": 412},
]
state.record = DEFAULT_RECORD.copy()
state.dialog = False
state.is_editing = False
state.headers = [
    {"title": "Title", "value": "title"},
    {"title": "Author", "value": "author"},
    {"title": "Genre", "value": "genre"},
    {"title": "Year", "value": "year"},
    {"title": "Pages", "value": "pages"},
    {"title": "Actions", "value": "actions", "sortable": False},
]


# Functions
@state.change("dialog")
def reset_dialog(dialog: Any, **kwargs: Any) -> None:
    if not dialog:
        state.record = DEFAULT_RECORD.copy()


def add_book() -> None:
    state.is_editing = False
    state.record = DEFAULT_RECORD.copy()
    state.dialog = True


@server.controller.trigger("edit_book")
def edit_book(book_id: str) -> None:
    state.is_editing = True
    book = next((b for b in state.books if b["id"] == book_id), None)
    if book:
        state.record = book.copy()
        state.dialog = True


def remove_book(book_id: str) -> None:
    state.books = [b for b in state.books if b["id"] != book_id]


@server.controller.trigger("save_book")
def save_book() -> None:
    if state.is_editing:
        for i, book in enumerate(state.books):
            if book["id"] == state.record["id"]:
                state.books[i] = state.record.copy()
                break
    else:
        state.record["id"] = len(state.books) + 1
        state.books.append(state.record.copy())
    state.dialog = False
    state.dirty("books")


# Bind functions to state
server.controller.add_book = add_book
server.controller.edit_book = edit_book
server.controller.remove_book = remove_book
server.controller.save_book = save_book

# UI
print(state.headers)
print(state.books)
with SinglePageLayout(server) as layout:
    layout.title.set_text("Popular Books")

    with layout.content:
        with vuetify.VSheet(classes="pa-4"):
            with vuetify.VDataTable(
                headers=("headers", []),
                items=("books", []),
            ):
                with vuetify.Template(v_slot_top=True):
                    with vuetify.VToolbar(flat=True):
                        vuetify.VToolbarTitle("Popular Books")
                        vuetify.VSpacer()
                        vuetify.VBtn(
                            "Add a Book",
                            prepend_icon="mdi-plus",
                            click=server.controller.add_book,
                        )

                with vuetify.Template(raw_attrs=['v-slot:item.actions="{ item }"']):
                    with html.Div(classes="d-flex justify-end"):
                        with vuetify.VBtn(icon=True, size="small", click="trigger('edit_book', [item.id])"):
                            vuetify.VIcon("mdi-pencil")

        with vuetify.VDialog(v_model="dialog", max_width="500px"):
            with vuetify.VCard():
                vuetify.VCardTitle("{{ is_editing ? 'Edit' : 'Add' }} a Book")
                vuetify.VCardSubtitle("{{ is_editing ? 'Update' : 'Create' }} your favorite book")
                with vuetify.VCardText():
                    vuetify.VTextField(v_model="record.title", label="Title", update_modelValue="flushState('record')")
                    vuetify.VTextField(v_model="record.author", label="Author")
                    vuetify.VSelect(
                        v_model="record.genre", items=["Fiction", "Dystopian", "Non-Fiction", "Sci-Fi"], label="Genre"
                    )
                    vuetify.VTextField(v_model="record.year", label="Year", type="number")
                    vuetify.VTextField(v_model="record.pages", label="Pages", type="number")
                with vuetify.VCardActions():
                    vuetify.VBtn("Cancel", click="dialog = False")
                    vuetify.VSpacer()
                    vuetify.VBtn("Save", click="trigger('save_book')")

# Start server
if __name__ == "__main__":
    server.start(open_browser=False)
