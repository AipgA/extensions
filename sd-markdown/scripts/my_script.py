from modules import script_callbacks, shared
import gradio as gr

def my_function(prompt):
    return f"你輸入了: {prompt}"

def on_ui_tabs():
    with gr.Blocks() as my_ui:
        gr.Markdown("## 🧩 我的擴充功能")
        with gr.Row():
            textbox = gr.Textbox(label="輸入一些文字")
        with gr.Row():
            output = gr.Textbox(label="輸出", interactive=False)
        textbox.change(fn=my_function, inputs=[textbox], outputs=[output])

    # Tab 標題與 ID 也可用中文
    return [(my_ui, "我的擴充功能", "我的擴充功能")]

def on_ui_settings():
    section = ("md_logger", "Markdown 記錄器")
    shared.opts.add_option(
        "enable_md_logger",
        shared.OptionInfo(
            True,
            "啟用圖片生成紀錄為 Markdown 檔案 以及批次歸檔",
            gr.Checkbox,
            {"interactive": True},
            section=section,
        ),
    )
    shared.opts.add_option(
        "md_logger_path",
        shared.OptionInfo(
            "",
            "自訂儲存路徑（留空則與圖片同資料夾）",
            gr.Textbox,
            {"interactive": True, "lines": 1},
            section=section,
        ),
    )
    shared.opts.add_option(
        "md_logger_path_custom",
        shared.OptionInfo(
            "",
            "自訂儲存名稱（留空則依照時間戳）",
            gr.Textbox,
            {"interactive": True, "lines": 1},
            section=section,
        ),
    )

script_callbacks.on_ui_settings(on_ui_settings)
script_callbacks.on_ui_tabs(on_ui_tabs)
