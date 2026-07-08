from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import gradio as gr

from src.frontend.api_client import ApiAuthError, ApiClient, ApiClientError
from src.utils.config import get_config_path, load_config

# Gradio's multiline Textbox submits on Enter regardless of the Shift key.
# It isn't watching keydown for this - it reacts to the native 'input' event
# the browser fires with inputType "insertLineBreak" once Enter's default
# newline action completes. So Shift+Enter can't just let the browser's
# default action happen (that's the event Gradio submits on); instead we
# preventDefault the native newline entirely and insert one ourselves via a
# synthetic 'input' event tagged as plain text, which Svelte's binding
# accepts as a normal edit without tripping Gradio's insertLineBreak check.
_ENTER_TO_SEND_JS = """
<script>
document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter') {
        return;
    }
    const textarea = e.target.closest && e.target.closest('#message_box textarea');
    if (!textarea) {
        return;
    }
    e.preventDefault();
    e.stopImmediatePropagation();
    if (e.shiftKey) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        textarea.value = textarea.value.slice(0, start) + '\\n' + textarea.value.slice(end);
        textarea.selectionStart = textarea.selectionEnd = start + 1;
        textarea.dispatchEvent(
            new InputEvent('input', { bubbles: true, cancelable: true, inputType: 'insertText', data: '\\n' })
        );
        return;
    }
    const wrapper = document.querySelector('#send_btn');
    const button = wrapper && (wrapper.tagName === 'BUTTON' ? wrapper : wrapper.querySelector('button'));
    if (button) {
        button.click();
    }
}, true);
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=EB+Garamond:wght@400;500;600&display=swap" rel="stylesheet">
"""

# "Dark" design: an immersive, moody dark mode leaning into Malifaux's
# gothic-horror atmosphere - near-black background, crimson/gold accents,
# an engraved-title display font - matching the wiki's palette in
# src/wiki/templates/base.html. Both the light and dark theme variants are
# set to the same dark values so it stays dark regardless of the browser's
# color-scheme preference.
_DARK_THEME = gr.themes.Base(
    primary_hue="red",
    secondary_hue="gray",
    neutral_hue="gray",
    font=gr.themes.GoogleFont("EB Garamond"),
    font_mono="ui-monospace",
).set(
    body_background_fill="#100d0f",
    body_background_fill_dark="#100d0f",
    body_text_color="#e8e0d5",
    body_text_color_dark="#e8e0d5",
    background_fill_secondary="#1c1719",
    background_fill_secondary_dark="#1c1719",
    border_color_primary="#2f2529",
    border_color_primary_dark="#2f2529",
    button_primary_background_fill="#b8283f",
    button_primary_background_fill_dark="#b8283f",
    button_primary_background_fill_hover="#d63a54",
    button_primary_background_fill_hover_dark="#d63a54",
    button_primary_text_color="#100d0f",
    button_primary_text_color_dark="#100d0f",
    block_title_text_color="#c9a227",
    block_title_text_color_dark="#c9a227",
    block_label_text_color="#c9a227",
    block_label_text_color_dark="#c9a227",
    block_background_fill="#1c1719",
    block_background_fill_dark="#1c1719",
    block_border_color="#2f2529",
    block_border_color_dark="#2f2529",
    input_background_fill="#1c1719",
    input_background_fill_dark="#1c1719",
    button_secondary_background_fill="#241c1f",
    button_secondary_background_fill_dark="#241c1f",
    button_secondary_background_fill_hover="#332830",
    button_secondary_background_fill_hover_dark="#332830",
    button_secondary_text_color="#e8e0d5",
    button_secondary_text_color_dark="#e8e0d5",
    button_secondary_border_color="#2f2529",
    button_secondary_border_color_dark="#2f2529",
)

_DARK_CSS = """
h1, .prose h1, .prose h2, .prose h3 { font-family: "Cinzel", Georgia, serif !important; color: #c9a227 !important; letter-spacing: 0.02em; }
.prose, .prose p, .prose li { color: #e8e0d5 !important; }
"""


def _humanize_document_id(document_id: str) -> str:
    return document_id.replace("_", " ").replace("-", " ").title()


def _format_citation_label(source: dict) -> str:
    name = _humanize_document_id(source["document_id"])
    if source["page_start"] == source["page_end"]:
        pages = f"p. {source['page_start']}"
    else:
        pages = f"pp. {source['page_start']}-{source['page_end']}"
    return f"{name} ({pages})"


def _pdf_viewer_html(api_base_url: str, document_id: str, page: int) -> str:
    """Embed the real PDF (not the processed text) at the given page, so the
    user reads the same document Buddharauer cites from."""
    url = f"{api_base_url}/api/documents/{document_id}/pdf#page={page}"
    title = _humanize_document_id(document_id)
    return (
        f'<iframe src="{url}" title="{title}" width="100%" height="700" '
        'style="border: 1px solid var(--border-color-primary, #444);"></iframe>'
    )


def build_app(client: ApiClient, api_base_url: str) -> gr.Blocks:
    def send_message(message, history, conversation_id, sources_state):
        history = history or []
        if not message.strip():
            yield history, gr.update(), sources_state, message
            return

        # Local LLM generation can take a while - show something immediately
        # rather than leaving the UI looking frozen/disconnected. The first
        # streamed token replaces this placeholder.
        thinking_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "_Thinking..._"},
        ]
        yield thinking_history, gr.update(), sources_state, ""

        answer = ""
        sources: list[dict] = []
        try:
            for event in client.send_chat_stream(message, conversation_id):
                event_type = event["type"]
                if event_type == "token":
                    answer += event["content"]
                    streaming_history = history + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": answer},
                    ]
                    yield streaming_history, gr.update(), sources_state, ""
                elif event_type == "done":
                    sources = event["sources"]
                elif event_type == "error":
                    error_history = history + [
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": event["detail"]},
                    ]
                    yield error_history, gr.update(choices=[]), sources_state, ""
                    return
        except ApiClientError as e:
            error_history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": f"Could not reach the backend: {e}"},
            ]
            yield error_history, gr.update(choices=[]), sources_state, ""
            return

        if sources:
            labels = [_format_citation_label(s) for s in sources]
            final_answer = answer + "\n\nSources: " + ", ".join(labels)
        else:
            labels = []
            final_answer = answer

        final_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": final_answer},
        ]
        yield final_history, gr.update(choices=labels, value=None), sources, ""

    def view_citation(citation_label, sources):
        if not citation_label or not sources:
            return ""
        labels = [_format_citation_label(s) for s in sources]
        if citation_label not in labels:
            return ""
        source = sources[labels.index(citation_label)]
        return _pdf_viewer_html(api_base_url, source["document_id"], source["page_start"])

    def refresh_documents():
        try:
            docs = client.list_documents()
        except ApiClientError as e:
            return gr.update(choices=[]), f"Could not reach the backend: {e}"
        if not docs:
            return gr.update(choices=[]), "No documents ingested yet."
        choices = [f"{d['id']} ({d['status']})" for d in docs]
        return gr.update(choices=choices), f"{len(docs)} document(s) found."

    def view_selected_document(doc_choice):
        if not doc_choice:
            return ""
        document_id = doc_choice.split(" (")[0]
        return _pdf_viewer_html(api_base_url, document_id, 1)

    def upload_document(file, admin_password):
        if file is None:
            return "No file selected."
        try:
            with open(file.name, "rb") as f:
                content = f.read()
            result = client.upload_document(os.path.basename(file.name), content, admin_password or "")
        except ApiAuthError:
            return "Incorrect admin password - upload rejected."
        except ApiClientError as e:
            return f"Upload failed: {e}"
        return (
            f"Uploaded '{result['document_id']}' - status: {result['status']}. "
            "Click 'Refresh document list' to check progress."
        )

    def unlock_admin(password):
        if not password:
            return gr.update(visible=False), "Enter the admin password.", None
        try:
            valid = client.verify_admin_password(password)
        except ApiClientError as e:
            return gr.update(visible=False), f"Could not reach the backend: {e}", None
        if not valid:
            return gr.update(visible=False), "Incorrect admin password.", None
        return gr.update(visible=True), "Unlocked.", password

    with gr.Blocks(
        title="Buddharauer", head=_ENTER_TO_SEND_JS, theme=_DARK_THEME, css=_DARK_CSS
    ) as demo:
        # A callable default is invoked fresh per browser session by Gradio -
        # a plain str(uuid.uuid4()) would be computed once at app-build time
        # and shared by every visitor.
        conversation_id = gr.State(lambda: str(uuid.uuid4()))
        sources_state = gr.State([])

        gr.Markdown("# Buddharauer - Malifaux Document Explorer")
        gr.HTML(f'<a href="{api_base_url}/wiki" target="_blank">Browse the Wiki</a>')

        with gr.Row():
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(label="Chat", height=500, type="messages")
                message_box = gr.Textbox(
                    label="Ask a question",
                    placeholder="Who is...? (Enter to send, Shift+Enter for a new line)",
                    lines=2,
                    elem_id="message_box",
                )
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary", elem_id="send_btn")
                    clear_btn = gr.Button("Clear chat")
                citation_radio = gr.Radio(
                    label="Citations from last answer",
                    choices=[],
                    interactive=True,
                    elem_id="citation_radio",
                )

            with gr.Column(scale=1):
                gr.Markdown("### Document Viewer")
                doc_dropdown = gr.Dropdown(label="Select document", choices=[], interactive=True)
                refresh_btn = gr.Button("Refresh document list")
                status_text = gr.Markdown("")
                doc_viewer = gr.HTML("Select a document or citation to view its PDF here.")

        send_btn.click(
            send_message,
            inputs=[message_box, chatbot, conversation_id, sources_state],
            outputs=[chatbot, citation_radio, sources_state, message_box],
        )
        message_box.submit(
            send_message,
            inputs=[message_box, chatbot, conversation_id, sources_state],
            outputs=[chatbot, citation_radio, sources_state, message_box],
        )
        clear_btn.click(
            lambda: ([], gr.update(choices=[]), []),
            outputs=[chatbot, citation_radio, sources_state],
        )

        citation_radio.change(view_citation, inputs=[citation_radio, sources_state], outputs=[doc_viewer])

        refresh_btn.click(refresh_documents, outputs=[doc_dropdown, status_text])
        doc_dropdown.change(view_selected_document, inputs=[doc_dropdown], outputs=[doc_viewer])

        demo.load(refresh_documents, outputs=[doc_dropdown, status_text])

    with demo.route("Admin", "/admin"):
        admin_password_state = gr.State(None)

        gr.Markdown("# Admin - Upload New PDFs")
        gr.Markdown("Enter the admin password to unlock the upload form.")

        unlock_password_box = gr.Textbox(label="Admin password", type="password")
        unlock_btn = gr.Button("Unlock", variant="primary")
        unlock_status = gr.Markdown("")

        with gr.Group(visible=False) as upload_group:
            upload_file = gr.File(label="PDF file", file_types=[".pdf"])
            upload_status = gr.Markdown("")

        unlock_btn.click(
            unlock_admin,
            inputs=[unlock_password_box],
            outputs=[upload_group, unlock_status, admin_password_state],
        )
        unlock_password_box.submit(
            unlock_admin,
            inputs=[unlock_password_box],
            outputs=[upload_group, unlock_status, admin_password_state],
        )

        upload_file.upload(
            upload_document, inputs=[upload_file, admin_password_state], outputs=[upload_status]
        )

    return demo


def main() -> None:
    config = load_config(get_config_path())
    client = ApiClient(config.frontend.api_base_url, timeout=config.frontend.request_timeout)
    demo = build_app(client, config.frontend.api_base_url)
    demo.launch(server_port=config.frontend.port)


if __name__ == "__main__":
    main()
