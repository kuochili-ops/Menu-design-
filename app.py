import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, URIAction
import io

# --- 頁面設定 ---
st.set_page_config(page_title="LINE Rich Menu 產生器", layout="wide")
st.title("🎨 3x2 半版圖文選單產生器")
st.markdown("上傳圖片並用手指/滑鼠縮放框選範圍，設定 6 個 LIFF 連結後即可發布。")

# --- 從 Secrets 讀取金鑰 ---
try:
    CHANNEL_ACCESS_TOKEN = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
    line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
except Exception:
    st.error("❌ 找不到 Secrets 設定！請在 Streamlit Cloud 設定 LINE_CHANNEL_ACCESS_TOKEN")
    st.stop()

# --- 1. 圖片上傳與框選 ---
st.header("第 1 步：框選背景圖")
img_file = st.file_uploader("上傳背景圖片 (建議解析度高於 2500x843)", type=['png', 'jpg', 'jpeg'])

if img_file:
    img = Image.open(img_file).convert("RGB") # 確保轉換為 RGB 格式
    
    # 使用 st_cropper 進行裁切，固定比例為 2500:843
    # 這裡移除了可能導致錯誤的 status=True 參數
    cropped_img = st_cropper(
        img, 
        aspect_ratio=(2500, 843), 
        box_color='#FFFFFF',
        should_resize_out=True
    )
    
    # 強制調整為 LINE 官方規定的半版尺寸
    final_image = cropped_img.resize((2500, 843))
    st.image(final_image, caption="📸 裁切預覽 (2500x843)", use_container_width=True)

    st.divider()

    # --- 2. 設定 LIFF 連結 ---
    st.header("第 2 步：設定 6 格 LIFF 連結")
    st.info("請依序填入連結，這 6 格將以 3x2 (上排3格、下排3格) 排列。")
    
    liff_links = []
    # 建立 3 欄 UI 來排列輸入框
    row1_cols = st.columns(3)
    row2_cols = st.columns(3)
    
    all_cols = row1_cols + row2_cols
    for i in range(6):
        with all_cols[i]:
            link = st.text_input(f"第 {i+1} 格 URL", placeholder="https://liff.line.me/...", key=f"link_{i}")
            liff_links.append(link)

    # --- 3. 執行發布 ---
    st.divider()
    if st.button("🚀 確認並發布至 LINE 官方帳號", use_container_width=True):
        if not all(liff_links):
            st.warning("⚠️ 請確認 6 個連結都已填寫完畢！")
        else:
            try:
                with st.spinner("⏳ 正在建立 Rich Menu 並上傳圖片..."):
                    # A. 定義 3x2 的點擊區域
                    cell_w = 2500 // 3
                    cell_h = 843 // 2
                    areas = []
                    for i in range(6):
                        row = i // 3
                        col = i % 3
                        areas.append(RichMenuArea(
                            bounds=RichMenuBounds(
                                x=col * cell_w, 
                                y=row * cell_h, 
                                width=cell_w, 
                                height=cell_h
                            ),
                            action=URIAction(label=f"Action_{i+1}", uri=liff_links[i])
                        ))

                    # B. 建立 Rich Menu 結構
                    rich_menu_to_create = RichMenu(
                        size=RichMenuSize(width=2500, height=843),
                        selected=True,
                        name="Custom_3x2_Menu",
                        chat_bar_text="選單功能",
                        areas=areas
                    )

                    # C. 呼叫 API
                    # 1. 建立選單 ID
                    rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu_to_create)
                    
                    # 2. 轉換圖片為 Byte 串流並上傳
                    img_byte_arr = io.BytesIO()
                    final_image.save(img_byte_arr, format='PNG')
                    line_bot_api.set_rich_menu_image(rich_menu_id, 'image/png', img_byte_arr.getvalue())
                    
                    # 3. 設為全體用戶的預設選單
                    line_bot_api.set_default_rich_menu(rich_menu_id)
                    
                    st.success(f"✨ 成功！新選單已生效。ID: {rich_menu_id}")
                    st.balloons()
                    st.info("提示：如果手機端沒看到更新，請嘗試重開 LINE 聊天室。")
            except Exception as e:
                st.error(f"❌ 發布失敗: {e}")

else:
    st.info("💡 請先上傳一張圖片，即可開始縮放裁切。")
