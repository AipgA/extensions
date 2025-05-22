import os
import re
import datetime
from modules import script_callbacks, shared

saved_images = []
saved_metadata = []  # 每張圖的 prompt、seed 等資料


def get_model_name(model_path):
    if not model_path:
        return ""
    base = os.path.basename(model_path)
    name, _ = os.path.splitext(base)
    return name


def get_vae_name(vae_path):
    if not vae_path:
        return ""
    base = os.path.basename(vae_path)
    name, _ = os.path.splitext(base)
    return name


def extract_lora_from_prompt(prompt):
    lora_list = []
    if not prompt:
        return lora_list
    pattern = r"<lora:([^:>]+):([\d\.]+)>"
    for match in re.finditer(pattern, prompt):
        name, weight = match.groups()
        lora_list.append({"name": name, "weight": weight})
    return lora_list


def custom_image_saved(params):
    global saved_images, saved_metadata
    if shared.opts.data.get("enable_md_logger", False) is False:
        return

    if hasattr(params, "filename") and isinstance(params.filename, str):
        # grid 圖片不記錄，只觸發總覽
        if "grid" in params.filename:
            on_image_grid()
            return

        saved_images.append(params.filename)

        # 優先從 params.p 取得 metadata
        p = getattr(params, "p", None)
        if p is not None:
            all_seeds = getattr(p, "all_seeds", None)
            if all_seeds and isinstance(all_seeds, list):
                idx = len(saved_images) - 1
                if 0 <= idx < len(all_seeds):
                    seed = all_seeds[idx]
                else:
                    seed = getattr(p, "seed", -1)
            else:
                seed = getattr(p, "seed", -1)
            prompt = getattr(p, "prompt", "")
            neg_prompt = getattr(p, "negative_prompt", "")
            # 模型名稱優先從 p 取，若無則從 shared.sd_model 取
            model = getattr(p, "sd_model_checkpoint", None)
            if model is None:
                model = (
                    getattr(shared.sd_model, "sd_model_checkpoint", None)
                    if getattr(shared, "sd_model", None) is not None
                    else None
                )
            sampler = getattr(p, "sampler_name", "")
            steps = getattr(p, "steps", None)
            cfg = getattr(p, "cfg_scale", None)
            width = getattr(p, "width", None)
            height = getattr(p, "height", None)
            # VAE 名稱擷取
            vae = getattr(p, "sd_vae", None)
            if not vae and hasattr(p, "override_settings"):
                vae = p.override_settings.get("sd_vae", "")
            if not vae:
                vae = shared.opts.data.get("sd_vae", "")
            # LoRA 內容擷取（從 prompt 解析）
            lora_list = extract_lora_from_prompt(prompt)
            lora_enabled = len(lora_list) > 0
            # 高解析修正判斷
            enable_hr = getattr(p, "enable_hr", False)
            hr_scale = getattr(p, "hr_scale", 1)
            hr_resize_x = getattr(p, "width", None)
            hr_resize_y = getattr(p, "height", None)
            hr_second_pass_steps = getattr(p, "hr_second_pass_steps", "")
            hr_upscaler = getattr(p, "hr_upscaler", "")
            denoising_strength = getattr(p, "denoising_strength", "")
            highres_fix = bool(enable_hr and hr_scale and hr_scale != 1)
        else:
            # fallback: 盡量從 shared 取得
            prompt = getattr(shared.state, "job_prompt", "")
            neg_prompt = getattr(shared.state, "job_negative_prompt", "")
            model = getattr(shared.sd_model, "sd_model_checkpoint", None)
            seed = getattr(shared.state, "job_no", -1)
            sampler = getattr(shared.opts, "sampler_name", "")
            steps = shared.opts.data.get("steps", 20)
            cfg = shared.opts.data.get("cfg_scale", 7)
            width = shared.opts.data.get("width", 512)
            height = shared.opts.data.get("height", 512)
            vae = shared.opts.data.get("sd_vae", "")
            lora_list = []
            lora_enabled = False
            highres_fix = False
            hr_scale = 1
            hr_resize_x = width
            hr_resize_y = height
            hr_second_pass_steps = ""
            hr_upscaler = ""
            denoising_strength = ""

        saved_metadata.append(
            {
                "prompt": prompt,
                "neg_prompt": neg_prompt,
                "model": model,
                "seed": seed,
                "sampler": sampler,
                "steps": steps,
                "cfg": cfg,
                "width": width,
                "height": height,
                "vae": vae,
                "lora_enabled": lora_enabled,
                "lora_list": lora_list,
                "highres_fix": highres_fix,
                "hr_scale": hr_scale,
                "hr_resize_x": hr_resize_x,
                "hr_resize_y": hr_resize_y,
                "hr_second_pass_steps": hr_second_pass_steps,
                "hr_upscaler": hr_upscaler,
                "denoising_strength": denoising_strength,
            }
        )

        print("已儲存:", params.filename)


def on_image_grid():
    global saved_images, saved_metadata
    if not saved_images:
        return

    now = datetime.datetime.now()
    batch_serial = now.strftime("%Y%m%d")

    base_folder_name = shared.opts.data.get("md_logger_path_custom", "").strip()
    if not base_folder_name:
        base_folder_name = batch_serial

    folder = os.path.join("outputs", base_folder_name)
    suffix = 1
    while os.path.exists(folder):
        folder = os.path.join("outputs", f"{base_folder_name}-{suffix}")
        suffix += 1
    os.makedirs(folder, exist_ok=True)

    # 處理最終尺寸顯示
    if saved_metadata:
        meta = saved_metadata[0]
        hr_scale = meta.get("hr_scale", 1)
        width = meta.get("width", 0)
        height = meta.get("height", 0)
        try:
            hr_scale_f = float(hr_scale)
        except Exception:
            hr_scale_f = 1
        if meta.get("highres_fix") and hr_scale_f > 1:
            try:
                target_x = int(width * hr_scale_f)
                target_y = int(height * hr_scale_f)
                target_resolution = f"{target_x}x{target_y}"
            except Exception:
                target_resolution = f"{width}x{height}"
        else:
            target_resolution = f"{width}x{height}"
    else:
        target_resolution = ""

    # 高解析補正區塊內容動態顯示
    if saved_metadata and saved_metadata[0]["highres_fix"]:
        hr_scale = saved_metadata[0]["hr_scale"]
        hr_second_pass_steps = saved_metadata[0]["hr_second_pass_steps"]
        hr_upscaler = saved_metadata[0]["hr_upscaler"]
        denoising_strength = saved_metadata[0]["denoising_strength"]
        target_res = target_resolution
    else:
        hr_scale = ""
        hr_second_pass_steps = ""
        hr_upscaler = ""
        denoising_strength = ""
        target_res = ""

    summary_lines = [
        "# Stable Diffusion 圖片生成紀錄\n",
        "## 📌 基本資訊",
        f"- **生成日期**：{batch_serial}",
        f"- **使用平台**：AUTOMATIC1111 WebUI",
        f"- **模型（Checkpoint）**：`{get_model_name(saved_metadata[0]['model']) if saved_metadata else ''}`",
        f"- **VAE**：`{get_vae_name(saved_metadata[0]['vae']) if saved_metadata else ''}`",
        (
            f"- **圖片尺寸**：{saved_metadata[0]['width']}x{saved_metadata[0]['height']}"
            if saved_metadata
            else "- **圖片尺寸**："
        ),
        f"- **種子（Seed）**：{saved_metadata[0]['seed'] if saved_metadata else ''}",
        f"- **步數（Steps）**：{saved_metadata[0]['steps'] if saved_metadata else ''}",
        f"- **採樣器（Sampler）**：{saved_metadata[0]['sampler'] if saved_metadata else ''}",
        f"- **CFG Scale**：{saved_metadata[0]['cfg'] if saved_metadata else ''}",
        "\n---\n",
        "## 🎨 LoRA 與其他附加模型",
        "| 名稱 | 權重（Weight） | 備註 |",
        "|------|----------------|------|",
    ]

    # LoRA 條列
    if saved_metadata and saved_metadata[0].get("lora_list"):
        for lora in saved_metadata[0]["lora_list"]:
            summary_lines.append(f"| `{lora['name']}` | {lora['weight']} |  |")
    else:
        summary_lines.append("| `` |  |  |")

    summary_lines += [
        "\n---\n",
        "## 🧠 Prompt 與 Negative Prompt",
        "\n### ✅ 正向提示詞（Prompt）",
        f"\n```\n{saved_metadata[0]['prompt'] if saved_metadata and len(saved_metadata) > 0 else ''}\n```",
        "\n### 🚫 反向提示詞（Negative Prompt）",
        f"\n```\n{saved_metadata[0]['neg_prompt'] if saved_metadata and len(saved_metadata) > 0 else ''}\n```",
        "\n---\n",
        "## 🔍 高解析補正（Highres. fix）",
        f"- **是否啟用**：{'✅' if saved_metadata and len(saved_metadata) > 0 and saved_metadata[0]['highres_fix'] else '❌'}",
        f"- **放大倍數（Upscale by）**：{hr_scale}",
        f"- **最終尺寸（Target resolution）**：{target_res}",
        f"- **重繪步數（Second pass steps）**：{hr_second_pass_steps}",
        f"- **Upscaler**：{hr_upscaler}",
        f"- **Denoising strength**：{denoising_strength}",
        "\n---\n",
        f"**圖片數量**：{len(saved_images)}\n",
        "| 編號 | 檔名 | 種子 |",
        "|------|------|------|",
    ]

    for idx, old_path in enumerate(saved_images):
        ext = os.path.splitext(old_path)[1]
        new_name = f"{batch_serial}-{idx+1:03d}{ext}"
        new_path = os.path.join(folder, new_name)
        os.rename(old_path, new_path)
        print(f"分類並重新命名: {old_path} -> {new_path}")

        if idx < len(saved_metadata):
            meta = saved_metadata[idx]
            summary_lines.append(f"| {idx+1} | {new_name} | {meta['seed']} |")

    summary_lines.append("\n## 📝 備註\n- \n- \n- \n")

    summary_md_path = os.path.join(folder, f"{batch_serial}_summary.md")
    with open(summary_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    saved_images.clear()
    saved_metadata.clear()
    print("所有圖片已分類、重新命名並建立總覽 .md")


script_callbacks.on_image_saved(custom_image_saved)
