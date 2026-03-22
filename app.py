import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, URIAction
import io

# --- 頁面設定 ---
st.set_page_config(page_title="LINE Rich Menu 產生器", layout="wide")
st.title("🎨 3x2 半版圖文選單產生器")

# --- 從 Secrets 讀取金鑰 ---
try:
    TOKEN = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
    line_bot_api = LineBotApi(TOKEN)
except Exception:
    st.error("❌ 找不到 Secrets 設定！請在 Streamlit Cloud 設定 LINE_CHANNEL_ACCESS_TOKEN")
    st.stop()

# --- 1. 圖片上傳與框選 ---
st.header("第 1 步：框選背景圖")
img_file = st.file_uploader("上傳背景圖片", type=['png', 'jpg', 'jpeg'])

if img_file:
    img = Image.open(img_file).convert("RGB")
    
    # 使用最簡化的參數，避免 TypeError
    # 這裡只保留必要的 img, aspect_ratio 和 box_color
    cropped_img = st_cropper(
        img, 
        aspect_ratio=(2500, 843), 
        box_color='#FFFFFF'
    )
    
    # 強制調整為 LINE 標準尺寸
    final_image = cropped_img.resize((2500, 843))
    st.image(final_image, caption="📸 裁切預覽 (2500x843)", use_container_width=True)

    st.divider()

    # --- 2. 設定 LIFF 連結 ---
    st.header("第 2 步：設定 6 格 LIFF 連結")
    liff_links = []
    col1, col2, col3 = st.columns(3)
    
    # 第一排 3 格
    with col1: liff_links.append(st.text_input("左上 (1)", "https://", key="l1"))
    with col2: liff_links.append(st.text_input("中上 (2)", "https://", key="l2"))
    with col3: liff_links.append(st.text_input("右上 (3)", "https://", key="l3"))
    # 第二排 3 格
    with col1: liff_links.append(st.text_input("左下 (4)", "https://", key="l4"))
    with col2: liff_links.append(st.text_input("中下 (5)", "https://", key="l5"))
    with col3: liff_links.append(st.text_input("右下 (6)", "https://", key="l6"))

    # --- 3. 執行發布 ---
    st.divider()
    if st.button("🚀 確認並發布至 LINE", use_container_width=True):
        try:
            with st.spinner("⏳ 正在更新選單..."):
                # A. 建立點擊區域 (3x2)
                w, h = 2500 // 3, 843 // 2
                areas = []
                for i in range(6):
                    areas.append(RichMenuArea(
                        bounds=RichMenuBounds(x=(i%3)*w, y=(i//3)*h, width=w, height=h),
                        action=URIAction(label=f"L_{i}", uri=liff_links[i])
                    ))

                # B. 建立與上傳
                rm_obj = RichMenu(
                    size=RichMenuSize(width=2500, height=843),
                    selected=True,
                    name="Auto_RichMenu",
                    chat_bar_text="開啟選單",
                    areas=areas
                )
                
                # 1. 取得新 ID
                rm_id = line_bot_api.create_rich_menu(rich_menu=rm_obj)
                
                # 2. 上傳圖
                img_io = io.BytesIO()
                final_image.save(img_io, format='PNG')
                line_bot_api.set_rich_menu_image(rm_id, 'image/png', img_io.getvalue())
                
                # 3. 設為預設
                line_bot_api.set_default_rich_menu(rm_id)
                
                st.success(f"✨ 已更新！ID: {rm_id}")
                
                # --- 自動清理舊選單 (選配) ---
                # 取得所有選單並刪除除了目前這個以外的所有選單，保持後台乾淨
                all_menus = line_bot_api.get_rich_menu_list()
                for m in all_menus:
                    if m.rich_menu_id != rm_id:
                        line_bot_api.delete_rich_menu(m.rich_menu_id)
                st.info("🧹 已自動清理舊的選單資料。")
                
        except Exception as e:
            st.error(f"❌ 錯誤: {e}")
else:
    st.info("💡 請先上傳圖片。")
