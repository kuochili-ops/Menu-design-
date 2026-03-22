def generate_rich_menu_object(liff_urls, menu_name="我的自定義選單"):
    # 這裡的 liff_urls 是一個包含 6 個連結的 list
    width = 2500
    height = 843
    cols = 3
    rows = 2
    
    cell_w = width // cols # 833
    cell_h = height // rows # 421
    
    areas = []
    for i in range(6):
        row = i // cols
        col = i % cols
        
        areas.append({
            "bounds": {
                "x": col * cell_w,
                "y": row * cell_h,
                "width": cell_w,
                "height": cell_h
            },
            "action": {
                "type": "uri",
                "label": f"Liff_{i+1}",
                "uri": liff_urls[i]
            }
        })
    
    return {
        "size": {"width": width, "height": height},
        "selected": True,
        "name": menu_name,
        "chatBarText": "查看更多功能",
        "areas": areas
    }
