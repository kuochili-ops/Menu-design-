import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, URIAction
import io

# 設定頁面與標題
st.set_page_config(page_title="LINE 3x2 選單產生器", layout="wide")
st.title("📸 3x2 半版選單：圖片縮放與框選")
st.write("操作指南：上傳圖片後，**移動或縮放圖片**使其進入白色框內即可。")

# 讀取 Secrets
try:
    TOKEN = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
    line_bot_api = LineBotApi(TOKEN)
except:
    st.error("❌ 請先在 Streamlit Cloud Secrets 設定 LINE_CHANNEL_ACCESS_TOKEN")
    st.stop()

# --- 第一步：圖片框選 (框固定，圖移動) ---
st.header("1. 調整圖片位置與大小")
img_file = st.file_uploader("請選擇要作為背景的圖片", type=['png', 'jpg', 'jpeg'])

if img_file:
    # 讀取並轉為 RGB 以利壓縮
    raw_img = Image.open(img_file).convert("RGB")
    
    # 呼叫裁切元件：
    # aspect_ratio 固定為半版規格
    # box_color 設為白色以對應你的需求
    cropped_img = st_cropper(
        raw_img, 
        aspect_ratio=(2500, 843), 
        box_color='#FFFFFF',
        key="cropper"
    )
    
    # 強制重繪為 LINE 標準尺寸 (2500x843)
    final_image = cropped_img.resize((2500, 843))
    st.image(final_image, caption="✨ 預期產出的選單樣貌", use_container_width=True)

    st.divider()

    # --- 第二步：設定 6 格連結 ---
    st.header("2. 設定 6 格 LIFF 連結 (3x2)")
    liff_links = []
    c1, c2, c3 = st.columns(3)
    # 依序產生 6 個輸入框
    for i in range(6):
        target_col = [c1, c2, c3][i % 3]
        with target_col:
            link = st.text_input(f"第 {i+1} 格 URL", "https://", key=f"url_{i}")
            liff_links.append(link)

    # --- 第三步：壓縮並發布 ---
    if st.button("🚀 壓縮圖片並發布至 LINE", use_container_width=True):
        try:
            with st.spinner("正在進行圖片瘦身與同步..."):
                # 建立 3x2 區域座標
                w, h = 2500 // 3, 843 // 2
                areas = [
                    RichMenuArea(
                        bounds=RichMenuBounds(x=(i%3)*w, y=(i//3)*h, width=w, height=h),
                        action=URIAction(label=f"Action_{i}", uri=liff_links[i])
                    ) for i in range(6)
                ]

                # 建立 Rich Menu 物件
                rm_obj = RichMenu(
                    size=RichMenuSize(width=2500, height=843),
                    selected=True,
                    name="Auto_Compressed_Menu",
                    chat_bar_text="打開選單",
                    areas=areas
                )
                
                # 1. 向 LINE 註冊選單
                rm_id = line_bot_api.create_rich_menu(rich_menu=rm_obj)
                
                # 2. 圖片瘦身處理：轉 JPEG 並壓縮畫質至 80%
                img_io = io.BytesIO()
                final_image.save(img_io, format='JPEG', quality=80, optimize=True)
                img_bytes = img_io.getvalue()
                
                # 3. 上傳圖片並設為預設
                line_bot_api.set_rich_menu_image(rm_id, 'image/jpeg', img_bytes)
                line_bot_api.set_default_rich_menu(rm_id)
                
                st.success(f"✅ 發布成功！(圖片已壓縮至 {len(img_bytes)/1024:.1f} KB)")
                st.balloons()

                # 4. 清理舊選單防止後台爆炸
                for old_menu in line_bot_api.get_rich_menu_list():
                    if old_menu.rich_menu_id != rm_id:
                        line_bot_api.delete_rich_menu(old_menu.rich_menu_id)
                st.info("🧹 已自動清理舊的選單 ID。")
                
        except Exception as e:
            st.error(f"❌ 錯誤: {e}")
else:
    st.info("請先上傳圖片，即可開始縮放裁切。")
