import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, URIAction
import io

# 頁面配置
st.set_page_config(page_title="LINE 選單製作器", layout="wide")
st.title("🎯 LINE 半版選單產生器")
st.markdown("### 操作說明：\n1. 上傳照片後，用手指**縮放或拖動照片**，使預想的畫面進入**白色固定框**內。\n2. 填寫 6 格 LIFF 連結後點擊發布。")

# 讀取 LINE 金鑰
try:
    TOKEN = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
    line_bot_api = LineBotApi(TOKEN)
except Exception:
    st.error("❌ 尚未設定 Secrets: LINE_CHANNEL_ACCESS_TOKEN")
    st.stop()

# --- 步驟 1: 圖片處理 (框固定在中間，圖片可動) ---
st.header("1. 調整選單背景")
img_file = st.file_uploader("上傳原始照片", type=['png', 'jpg', 'jpeg'])

if img_file:
    # 讀取並轉換為 RGB (避免透明層導致壓縮失敗)
    raw_img = Image.open(img_file).convert("RGB")
    
    # st_cropper 關鍵設定：
    # aspect_ratio: 固定為 2500:843 比例
    # box_color: 白色框
    # 執行時，框會固定在中間，你可以縮放/移動底層圖片
    cropped_img = st_cropper(
        raw_img, 
        aspect_ratio=(2500, 843), 
        box_color='#FFFFFF',
        key="rich_menu_cropper"
    )
    
    # 將裁切結果強制調整為 LINE 官方標準尺寸
    final_image = cropped_img.resize((2500, 843))
    st.image(final_image, caption="📸 即將發布的選單預覽", use_container_width=True)

    st.divider()

    # --- 步驟 2: 設定連結 (3x2 佈局) ---
    st.header("2. 設定點擊連結 (3x2)")
    liff_links = []
    c1, c2, c3 = st.columns(3)
    
    # 產生 6 個輸入框
    for i in range(6):
        target_col = [c1, c2, c3][i % 3]
        with target_col:
            label = "上排" if i < 3 else "下排"
            pos = ["左", "中", "右"][i % 3]
            link = st.text_input(f"{label}-{pos} ({i+1})", "https://", key=f"url_{i}")
            liff_links.append(link)

    # --- 步驟 3: 壓縮與上傳 ---
    st.divider()
    if st.button("🚀 壓縮圖片並更新 LINE 選單", use_container_width=True):
        try:
            with st.spinner("正在執行圖片瘦身與 API 同步..."):
                # A. 計算 6 格座標
                w, h = 2500 // 3, 843 // 2
                areas = [
                    RichMenuArea(
                        bounds=RichMenuBounds(x=(i%3)*w, y=(i//3)*h, width=w, height=h),
                        action=URIAction(label=f"L_{i+1}", uri=liff_links[i])
                    ) for i in range(6)
                ]

                # B. 建立 Rich Menu 架構
                rm_obj = RichMenu(
                    size=RichMenuSize(width=2500, height=843),
                    selected=True,
                    name="Streamlit_Auto_Menu",
                    chat_bar_text="功能選單",
                    areas=areas
                )
                
                # 1. 向 LINE 申請新選單 ID
                rm_id = line_bot_api.create_rich_menu(rich_menu=rm_obj)
                
                # 2. 核心：圖片瘦身處理 (轉 JPEG + 壓縮品質 80%)
                # 這樣即使原圖幾 MB，產出也會控制在 200KB 左右，遠低於 1MB 限制
                img_io = io.BytesIO()
                final_image.save(img_io, format='JPEG', quality=80, optimize=True)
                img_bytes = img_io.getvalue()
                
                # 3. 上傳圖片並啟用
                line_bot_api.set_rich_menu_image(rm_id, 'image/jpeg', img_bytes)
                line_bot_api.set_default_rich_menu(rm_id)
                
                st.success(f"✅ 更新成功！(圖片已壓縮至 {len(img_bytes)/1024:.1f} KB)")
                st.balloons()

                # 4. 自動清理舊選單，保持 LINE 後台整潔
                old_menus = line_bot_api.get_rich_menu_list()
                for m in old_menus:
                    if m.rich_menu_id != rm_id:
                        line_bot_api.delete_rich_menu(m.rich_menu_id)
                st.info("🧹 已自動刪除過期的舊選單配置。")
                
        except Exception as e:
            st.error(f"❌ 發生錯誤: {e}")
else:
    st.info("👋 請先從上方上傳一張照片。")
