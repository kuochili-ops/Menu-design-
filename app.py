import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, URIAction
import io

# --- 頁面設定 ---
st.set_page_config(page_title="LINE Rich Menu 產生器 (含圖片壓縮)", layout="wide")
st.title("🎨 3x2 半版圖文選單產生器")
st.markdown("上傳圖片，用手指縮放移動圖片至合適位置。系統會自動裁切並壓縮圖片。")

# --- 從 Secrets 讀取金鑰 ---
try:
    TOKEN = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
    line_bot_api = LineBotApi(TOKEN)
except Exception:
    st.error("❌ 找不到 Secrets 設定！請在 Streamlit Cloud 設定 LINE_CHANNEL_ACCESS_TOKEN")
    st.stop()

# --- 1. 圖片上傳與框選 ---
st.header("第 1 步：框選背景圖")
img_file = st.file_uploader("上傳背景圖片 (支援 JPG, PNG)", type=['png', 'jpg', 'jpeg'])

if img_file:
    # 讀取圖片並確保為 RGB 格式
    img = Image.open(img_file).convert("RGB")
    
    # 使用 st_cropper 進行裁切
    # 這裡只保留必要的參數，以確保最大的相容性
    # aspect_ratio=(2500, 843) 確保裁切框比例固定
    cropped_img = st_cropper(
        img, 
        aspect_ratio=(2500, 843), 
        box_color='#FFFFFF'
    )
    
    # 將裁切後的圖片調整為 LINE 標準尺寸
    final_image = cropped_img.resize((2500, 843))
    
    # 預覽裁切結果
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

    # --- 3. 執行發布與圖片壓縮 ---
    st.divider()
    if st.button("🚀 確認並壓縮發布至 LINE", use_container_width=True):
        try:
            with st.spinner("⏳ 正在壓縮圖片並更新選單..."):
                # A. 建立點擊區域 (3x2)
                w, h = 2500 // 3, 843 // 2
                areas = []
                for i in range(6):
                    areas.append(RichMenuArea(
                        bounds=RichMenuBounds(x=(i%3)*w, y=(i//3)*h, width=w, height=h),
                        action=URIAction(label=f"Action_{i+1}", uri=liff_links[i])
                    ))

                # B. 建立與上傳
                rm_obj = RichMenu(
                    size=RichMenuSize(width=2500, height=843),
                    selected=True,
                    name="Auto_RichMenu_Compressed",
                    chat_bar_text="開啟選單",
                    areas=areas
                )
                
                # 1. 取得新 ID
                rm_id = line_bot_api.create_rich_menu(rich_menu=rm_obj)
                
                # --- 核心：圖片瘦身/壓縮處理 ---
                img_io = io.BytesIO()
                # 將圖片儲存為 JPEG 格式，並設定 quality 參數進行壓縮
                # quality=85 通常可以在大幅減少檔案大小的同時，保持肉眼難以察覺的畫質損失
                # 如果檔案仍然太大，可以嘗試將 quality 降低 (例如 70 或 60)
                final_image.save(img_io, format='JPEG', quality=85)
                img_bytes = img_io.getvalue()
                
                # 檢查壓縮後的檔案大小 (選擇性)
                file_size_kb = len(img_bytes) / 1024
                st.write(f"ℹ️ 壓縮後圖片大小: {file_size_kb:.2f} KB")
                
                # 2. 上傳壓縮後的圖片
                line_bot_api.set_rich_menu_image(rm_id, 'image/jpeg', img_bytes)
                
                # 3. 設為預設
                line_bot_api.set_default_rich_menu(rm_id)
                
                st.success(f"✨ 已成功發布新選單！ID: {rm_id}")
                
                # --- 自動清理舊選單 ---
                all_menus = line_bot_api.get_rich_menu_list()
                for m in all_menus:
                    if m.rich_menu_id != rm_id:
                        line_bot_api.delete_rich_menu(m.rich_menu_id)
                st.info("🧹 已自動清理舊的選單資料。")
                
        except Exception as e:
            st.error(f"❌ 錯誤: {e}")
            st.warning("請確保圖片符合 LINE 的限制，並已填寫所有連結。")
else:
    st.info("💡 請先上傳圖片。")
