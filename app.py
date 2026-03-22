import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, URIAction
import io

# 頁面配置
st.set_page_config(page_title="LINE 3x2 選單產生器", layout="wide")
st.title("🎯 專業版圖文選單產生器")
st.markdown("### 1. 調整背景圖片 (框固定，圖可動)\n請縮放或移動照片，使其完美填滿白色框。")

# 讀取 LINE 金鑰
try:
    TOKEN = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
    line_bot_api = LineBotApi(TOKEN)
except Exception:
    st.error("❌ 尚未設定 Secrets: LINE_CHANNEL_ACCESS_TOKEN")
    st.stop()

# --- 步驟 1: 圖片處理 ---
img_file = st.file_uploader("上傳原始照片", type=['png', 'jpg', 'jpeg'])

if img_file:
    raw_img = Image.open(img_file).convert("RGB")
    
    # 框固定在中央，比例 2500:843
    cropped_img = st_cropper(
        raw_img, 
        aspect_ratio=(2500, 843), 
        box_color='#FFFFFF',
        key="rich_menu_cropper"
    )
    
    # 強制重繪為標準尺寸
    final_image = cropped_img.resize((2500, 843))
    st.image(final_image, caption="📸 選單預覽 (2500x843)", use_container_width=True)

    st.divider()

    # --- 步驟 2: 設定 6 格名稱與連結 (3x2) ---
    st.header("2. 設定 6 格 LIFF 功能資訊")
    
    menu_data = []
    # 使用 3 欄排列，每欄放兩格（上下排）
    c1, c2, c3 = st.columns(3)
    
    for i in range(6):
        target_col = [c1, c2, c3][i % 3]
        pos_text = ["左上", "中上", "右上", "左下", "中下", "右下"][i]
        with target_col:
            st.subheader(f"第 {i+1} 格 ({pos_text})")
            name = st.text_input(f"App 名稱", value=f"功能 {i+1}", key=f"name_{i}")
            url = st.text_input(f"LIFF URL", value="https://", key=f"url_{i}")
            menu_data.append({"name": name, "url": url})

    # --- 步驟 3: 瘦身與發布 ---
    st.divider()
    if st.button("🚀 壓縮並同步至 LINE 帳號", use_container_width=True):
        if any(not d["url"].startswith("https://") for d in menu_data):
            st.error("❌ 請確保所有連結皆以 https:// 開頭")
        else:
            try:
                with st.spinner("正在進行圖片壓縮與選單建置..."):
                    # A. 建立點擊區域，加入自定義 Label
                    w, h = 2500 // 3, 843 // 2
                    areas = [
                        RichMenuArea(
                            bounds=RichMenuBounds(x=(i%3)*w, y=(i//3)*h, width=w, height=h),
                            action=URIAction(label=menu_data[i]["name"], uri=menu_data[i]["url"])
                        ) for i in range(6)
                    ]

                    # B. 建立 Rich Menu
                    rm_obj = RichMenu(
                        size=RichMenuSize(width=2500, height=843),
                        selected=True,
                        name="Custom_RichMenu",
                        chat_bar_text="打開選單",
                        areas=areas
                    )
                    
                    # 1. 向 LINE 註冊
                    rm_id = line_bot_api.create_rich_menu(rich_menu=rm_obj)
                    
                    # 2. 圖片瘦身 (JPEG 壓縮至 80%)
                    img_io = io.BytesIO()
                    final_image.save(img_io, format='JPEG', quality=80, optimize=True)
                    img_bytes = img_io.getvalue()
                    
                    # 3. 上傳並啟用
                    line_bot_api.set_rich_menu_image(rm_id, 'image/jpeg', img_bytes)
                    line_bot_api.set_default_rich_menu(rm_id)
                    
                    st.success(f"✅ 更新成功！(圖片大小: {len(img_bytes)/1024:.1f} KB)")
                    st.balloons()

                    # 4. 清理舊選單
                    for old_m in line_bot_api.get_rich_menu_list():
                        if old_m.rich_menu_id != rm_id:
                            line_bot_api.delete_rich_menu(old_m.rich_menu_id)
                    st.info("🧹 已清理舊的選單 ID。")
                    
            except Exception as e:
                st.error(f"❌ 發生錯誤: {e}")
else:
    st.info("👋 請上傳照片開始製作。")
