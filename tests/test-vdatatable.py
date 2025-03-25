from trame.app import get_server
from trame.widgets import vuetify, html
from trame.ui.vuetify import SinglePageLayout

server = get_server(client_type="vue2")
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
    {"id": 3, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "genre": "Fiction", "year": 1925, "pages": 180},
    {"id": 4, "title": "Sapiens", "author": "Yuval Noah Harari", "genre": "Non-Fiction", "year": 2011, "pages": 443},
    {"id": 5, "title": "Dune", "author": "Frank Herbert", "genre": "Sci-Fi", "year": 1965, "pages": 412},
]
state.record = DEFAULT_RECORD.copy()
state.dialog = False
state.is_editing = False
state.headers=[
                    {"text": "Title", "value": "title"},
                    {"text": "Author", "value": "author"},
                    {"text": "Genre", "value": "genre"},
                    {"text": "Year", "value": "year"},
                    {"text": "Pages", "value": "pages"},
                    {"text": "Actions", "value": "actions", "sortable": False},
                ]

# Functions
@state.change("dialog")
def reset_dialog(dialog, **kwargs):
    if not dialog:
        state.record = DEFAULT_RECORD.copy()

def add_book():
    state.is_editing = False
    state.record = DEFAULT_RECORD.copy()
    state.dialog = True

def edit_book(book_id):
    state.is_editing = True
    book = next((b for b in state.books if b["id"] == book_id), None)
    if book:
        state.record = book.copy()
        state.dialog = True

def remove_book(book_id):
    state.books = [b for b in state.books if b["id"] != book_id]

def save_book():
    if state.is_editing:
        for i, book in enumerate(state.books):
            if book["id"] == state.record["id"]:
                state.books[i] = state.record.copy()
                break
    else:
        state.record["id"] = len(state.books) + 1
        state.books.append(state.record.copy())
    state.dialog = False

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
                #v_model="selected",
                headers=("headers",[]),
                #headers=[
                #    {"text": "Title", "value": "title"},
                #    {"text": "Author", "value": "author"},
                #    {"text": "Genre", "value": "genre"},
                #    {"text": "Year", "value": "year"},
                #    {"text": "Pages", "value": "pages"},
                #    {"text": "Actions", "value": "actions", "sortable": False},
                #],
                items=("books",[]),
                #hide_default_footer=("len(books) < 11",),
            ):
                with vuetify.Template(v_slot="top"):
                    with vuetify.VToolbar(flat=True):
                        vuetify.VToolbarTitle("Popular Books")
                        vuetify.VSpacer()
                        vuetify.VBtn(
                            "Add a Book",
                            prepend_icon="mdi-plus",
                            click="controller.add_book",
                        )
##
#                with vuetify.Template(v_slot="item.actions", slot_props="props"):
#                    with html.Div(classes="d-flex justify-end"):
#                        vuetify.VIcon(
#                            "mdi-pencil",
#                            small=True,
#                            click=("controller.edit_book(props.item.id)",)
#                        )
#                        vuetify.VIcon(
#                            "mdi-delete",
#                            small=True,
#                            click=("controller.remove_book(props.item.id)",),
#                        )

#                with vuetify.Template(v_slot="no-data"):
#                    vuetify.VBtn(
#                        "Reset Data",
#                        prepend_icon="mdi-backup-restore",
#                        click="reset_dialog",
#                    )
                pass
#
#        with vuetify.VDialog(v_model=("dialog",), max_width="500px"):
#            with vuetify.VCard():
#                vuetify.VCardTitle(
#                    "{{ 'Edit' if is_editing else 'Add' }} a Book"
#                )
#                vuetify.VCardSubtitle(
#                    "{{ 'Update' if is_editing else 'Create' }} your favorite book"
#                )
#                with vuetify.VCardText():
#                    with vuetify.VRow():
#                        vuetify.VCol(
#                            vuetify.VTextField(
#                                v_model=("record.title",), label="Title"
#                            ),
#                            cols=12,
#                        )
#                        vuetify.VCol(
#                            vuetify.VTextField(
#                                v_model=("record.author",), label="Author"
#                            ),
#                            cols=12,
#                            md=6,
#                        )
#                        vuetify.VCol(
#                            vuetify.VSelect(
#                                v_model=("record.genre",),
#                                items=["Fiction", "Dystopian", "Non-Fiction", "Sci-Fi"],
#                                label="Genre",
#                            ),
#                            cols=12,
#                            md=6,
#                        )
#                        vuetify.VCol(
#                            vuetify.VTextField(
#                                v_model=("record.year",), label="Year", type="number"
#                            ),
#                            cols=12,
#                            md=6,
#                        )
#                        vuetify.VCol(
#                            vuetify.VTextField(
#                                v_model=("record.pages",), label="Pages", type="number"
#                            ),
#                            cols=12,
#                            md=6,
#                        )
#                with vuetify.VCardActions():
#                    vuetify.VBtn("Cancel", click="dialog = False")
#                    vuetify.VSpacer()
#                    vuetify.VBtn("Save", click="controller.save_book")

# Start server
if __name__ == "__main__":
    server.start()
