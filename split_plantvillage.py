import os
import shutil


# Đường dẫn gốc chứa dataset PlantVillage (sửa lại cho đúng với máy bạn)
# Ví dụ: r"D:\BkStar\TomatoLeaf\PlantVillage"
SRC_ROOT = r"D:\BkStar\TomatoLeaf\PlantVillage"

# Thư mục đích muốn lưu dataset đã tách 3 bệnh
DST_ROOT = r"D:\BkStar\TomatoLeaf\dataset"

# Map tên folder gốc trong PlantVillage -> tên folder mới
# Lưu ý: tên thật trong thư mục của bạn là:
# - Tomato_Early_blight
# - Tomato_Bacterial_spot
# - Tomato__Tomato_YellowLeaf__Curl_Virus
CLASS_MAP = {
    "Tomato_Early_blight": "Early_blight",
    "Tomato_Bacterial_spot": "Bacterial_spot",
    "Tomato__Tomato_YellowLeaf__Curl_Virus": "Yellow_Leaf_Curl_Virus",
}


def copy_selected_classes(src_root: str, dst_root: str, class_map: dict) -> None:
    """Copy 3 lớp bệnh từ PlantVillage sang thư mục mới.

    - src_root: thư mục gốc PlantVillage (chứa các folder Tomato___...)
    - dst_root: thư mục đích để tạo `Early_blight`, `Bacterial_spot`, `Yellow_Leaf_Curl_Virus`
    - class_map: map từ tên folder gốc -> tên folder mới
    """
    os.makedirs(dst_root, exist_ok=True)

    for src_name, dst_name in class_map.items():
        src_dir = os.path.join(src_root, src_name)
        dst_dir = os.path.join(dst_root, dst_name)

        if not os.path.isdir(src_dir):
            print(f"[CẢNH BÁO] Không tìm thấy thư mục nguồn: {src_dir}")
            continue

        os.makedirs(dst_dir, exist_ok=True)

        num_files = 0
        for fname in os.listdir(src_dir):
            src_path = os.path.join(src_dir, fname)
            dst_path = os.path.join(dst_dir, fname)

            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
                num_files += 1

        print(f"Đã copy {num_files} file từ '{src_name}' sang '{dst_dir}'")


if __name__ == "__main__":
    print("Bắt đầu tách 3 lớp bệnh từ PlantVillage...")
    print(f"Thư mục nguồn: {SRC_ROOT}")
    print(f"Thư mục đích: {DST_ROOT}")
    copy_selected_classes(SRC_ROOT, DST_ROOT, CLASS_MAP)
    print("Hoàn tất.")

