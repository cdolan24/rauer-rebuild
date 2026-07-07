from __future__ import annotations

import os
import re
import sys
import uuid
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import gradio as gr

from src.frontend.api_client import ApiAuthError, ApiClient, ApiClientError
from src.utils.config import load_config

_PAGE_MARKER_RE = re.compile(r"--- page (\d+) ---\n")


def _extract_page_range(content: str, page_start: int, page_end: int) -> str:
    """Pull out just the pages a citation refers to from a document's full text."""
    matches = list(_PAGE_MARKER_RE.finditer(content))
    if not matches:
        return content

    sections = []
    for i, m in enumerate(matches):
        page_num = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        if page_start <= page_num <= page_end:
            sections.append(f"--- page {page_num} ---\n{content[start:end]}")
    return "\n".join(sections) if sections else content


def _format_citation_label(source: dict) -> str:
    if source["page_start"] == source["page_end"]:
        pages = f"p. {source['page_start']}"
    else:
        pages = f"pp. {source['page_start']}-{source['page_end']}"
    return f"{source['document_id']} ({pages})"


def _pdf_link_html(api_base_url: str, document_id: str, page: int) -> str:
    url = f"{api_base_url}/api/documents/{document_id}/pdf#page={page}"
    return f'<a href="{url}" target="_blank">View original PDF (page {page})</a>'


def build_app(client: ApiClient, api_base_url: str) -> gr.Blocks:
    def send_message(message, history, conversation_id, sources_state):
        history = history or []
        if not message.strip():
            yield history, gr.update(), sources_state, message
            return

        # Local LLM generation can take a while - show something immediately
        # rather than leaving the UI looking frozen/disconnected.
        thinking_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "_Thinking..._"},
        ]
        yield thinking_history, gr.update(), sources_state, ""

        try:
            result = client.send_chat(message, conversation_id)
        except ApiClientError as e:
            error_history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": f"Could not reach the backend: {e}"},
            ]
            yield error_history, gr.update(choices=[]), sources_state, ""
            return

        sources = result["sources"]
        if sources:
            labels = [_format_citation_label(s) for s in sources]
            answer = result["response"] + "\n\nSources: " + ", ".join(labels)
        else:
            labels = []
            answer = result["response"]

        final_history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": answer},
        ]
        yield final_history, gr.update(choices=labels, value=None), sources, ""

    def view_citation(citation_label, sources):
        if not citation_label or not sources:
            return "", ""
        labels = [_format_citation_label(s) for s in sources]
        if citation_label not in labels:
            return "", ""
        source = sources[labels.index(citation_label)]
        pdf_link = _pdf_link_html(api_base_url, source["document_id"], source["page_start"])
        try:
            content = client.get_document_content(source["document_id"])
        except ApiClientError as e:
            return f"Could not load document: {e}", pdf_link
        return _extract_page_range(content, source["page_start"], source["page_end"]), pdf_link

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
            return "", ""
        document_id = doc_choice.split(" (")[0]
        pdf_link = _pdf_link_html(api_base_url, document_id, 1)
        try:
            return client.get_document_content(document_id), pdf_link
        except ApiClientError as e:
            return f"Could not load document: {e}", pdf_link

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

    with gr.Blocks(title="Buddharauer") as demo:
        conversation_id = gr.State(str(uuid.uuid4()))
        sources_state = gr.State([])

        gr.Markdown("# Buddharauer - Malifaux Document Explorer")
        gr.HTML(f'<a href="{api_base_url}/wiki" target="_blank">Browse the Wiki</a>')

        with gr.Row():
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(label="Chat", height=500, type="messages")
                message_box = gr.Textbox(label="Ask a question", placeholder="Who is...?", lines=2)
                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary")
                    clear_btn = gr.Button("Clear chat")
                citation_dropdown = gr.Dropdown(
                    label="Citations from last answer", choices=[], interactive=True
                )

            with gr.Column(scale=1):
                gr.Markdown("### Document Viewer")
                doc_dropdown = gr.Dropdown(label="Select document", choices=[], interactive=True)
                refresh_btn = gr.Button("Refresh document list")
                status_text = gr.Markdown("")
                pdf_link_html = gr.HTML("")
                doc_viewer = gr.Textbox(label="Content", lines=25, interactive=False)

        send_btn.click(
            send_message,
            inputs=[message_box, chatbot, conversation_id, sources_state],
            outputs=[chatbot, citation_dropdown, sources_state, message_box],
        )
        message_box.submit(
            send_message,
            inputs=[message_box, chatbot, conversation_id, sources_state],
            outputs=[chatbot, citation_dropdown, sources_state, message_box],
        )
        clear_btn.click(
            lambda: ([], gr.update(choices=[]), []),
            outputs=[chatbot, citation_dropdown, sources_state],
        )

        citation_dropdown.change(
            view_citation, inputs=[citation_dropdown, sources_state], outputs=[doc_viewer, pdf_link_html]
        )

        refresh_btn.click(refresh_documents, outputs=[doc_dropdown, status_text])
        doc_dropdown.change(
            view_selected_document, inputs=[doc_dropdown], outputs=[doc_viewer, pdf_link_html]
        )

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
    config = load_config()
    client = ApiClient(config.frontend.api_base_url, timeout=config.frontend.request_timeout)
    demo = build_app(client, config.frontend.api_base_url)
    demo.launch(server_port=config.frontend.port)


if __name__ == "__main__":
    main()
