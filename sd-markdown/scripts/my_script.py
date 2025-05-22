from modules import script_callbacks, shared
import gradio as gr


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
