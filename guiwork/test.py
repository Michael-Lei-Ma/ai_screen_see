# -*- coding: utf-8 -*-
import os
import glob


# image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'screenshot_basic_info.png')
# print(image_path)
#
# # 定位 images 文件夹下所有 .png 文件
# # 这里使用相对路径，代表当前项目根目录下的 images 文件夹
# png_files = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),"images", "*.png"))
# # print(f'{os.path.join(os.path.dirname(os.path.abspath(__file__)),"images", "*.png")}\npng_files: {png_files}')
# # 删除所有找到的 .png 文件
# for file_path in png_files:
#     try:
#         os.remove(file_path)
#         print(f"已删除：{file_path}")
#     except Exception as e:
#         print(f"删除失败 {file_path}：{str(e)}")
#
# print("批量删除 .png 完成！")


#
# import win32crypt
#
# # 加密
# data = b"hello"
#
# encrypted = win32crypt.CryptProtectData(
#     data,
#     None,
#     None,
#     None,
#     None,
#     0
# )
# print(f"encrypted: {encrypted}")
# # 解密
# decrypted = win32crypt.CryptUnprotectData(
#     encrypted,
#     None,
#     None,
#     None,
#     0
# )
#
# print(decrypted[1])


# from PIL import Image
# import os
# from pathlib import Path
#
#
# def compress_png_pillow(input_path, output_dir="compress", quality=85):
#     """
#     使用 Pillow 压缩 PNG 图片
#
#     Args:
#         input_path: 输入图片路径
#         output_dir: 输出文件夹名称，默认为 compress
#         quality: 压缩质量 (1-100，默认85)
#     """
#     # 创建输出文件夹
#     project_str = os.path.dirname(__file__)
#     output_dir_path  = os.path.join(project_str,output_dir)
#     os.makedirs(output_dir_path, exist_ok=True)
#     output_path = Path(output_dir_path)
#     output_path.mkdir(exist_ok=True)
#
#     input_path = Path(os.path.join(project_str,input_path))
#     # 打开图片
#     img = Image.open(input_path)
#
#     # 生成输出文件名
#     input_filename = Path(input_path).stem
#     output_file = output_path / f"{input_filename}_compressed.png"
#
#     # 压缩并保存
#     # optimize=True 进行优化压缩
#     # quality 参数对 PNG 有效，但 Pillow 的 PNG 保存主要使用 compress_level
#     img.save(
#         output_file,
#         'PNG',
#         optimize=True,
#         compress_level=9  # 0-9，9为最高压缩
#     )
#
#     # 计算压缩前后的文件大小
#     original_size = os.path.getsize(input_path) / 1024  # KB
#     compressed_size = os.path.getsize(output_file) / 1024  # KB
#     compression_ratio = (1 - compressed_size / original_size) * 100
#
#     print(f"原图大小: {original_size:.2f} KB")
#     print(f"压缩后大小: {compressed_size:.2f} KB")
#     print(f"压缩率: {compression_ratio:.2f}%")
#
#     return output_file
#
#
# # 使用示例
# if __name__ == "__main__":
#
#     compress_png_pillow("screenshot_basic_info.png")
#     # output_dir = 'compress'
#     # input_path = "screenshot_basic_info.png"
#     # # project_str = os.path.dirname(__file__)
#     # project_str =str(Path.cwd())
#     # output_dir_path = os.path.join(project_str, output_dir)
#     # os.makedirs(output_dir_path, exist_ok=True)
#     # output_path = Path(output_dir_path)
#     # output_path.mkdir(exist_ok=True)
#     #
#     # input_path = Path(os.path.join(project_str, input_path))
#     # print(f"output_path: {output_path}  {type(output_path)}\ninput_path: {input_path}  {type(input_path)}")
#     #
#     # print(f"{ Path.cwd()} {type( Path.cwd())}")


from PIL import Image
import os
import shutil
from pathlib import Path
import io


class PNGCompressor:
    """PNG 图片压缩和解压（还原）工具类"""

    def __init__(self, project_root=None):
        """
        初始化

        Args:
            project_root: 项目根目录，默认为当前脚本所在目录
        """
        if project_root is None:
            self.project_root = Path.cwd()
        else:
            self.project_root = Path(project_root)

        self.compress_dir = self.project_root / "compress"
        self.unzip_dir = self.project_root / "unzip"

        # 创建必要的文件夹
        self.compress_dir.mkdir(exist_ok=True)
        self.unzip_dir.mkdir(exist_ok=True)

    def compress_png(self, input_path, compress_level=9, keep_original=False):
        """
        压缩 PNG 图片并保存到 compress 文件夹

        Args:
            input_path: 原始 PNG 图片路径
            compress_level: 压缩级别 (0-9，9为最高压缩)
            keep_original: 是否保留原图文件名（False则添加_compressed后缀）

        Returns:
            Path: 压缩后的文件路径
        """
        input_path = Path(input_path)

        if not input_path.exists():
            raise FileNotFoundError(f"文件不存在: {input_path}")

        if input_path.suffix.lower() not in ['.png', '.PNG']:
            raise ValueError(f"不支持的文件格式，仅支持 PNG: {input_path}")

        # 生成输出文件名
        if keep_original:
            output_filename = input_path.name
        else:
            output_filename = f"{input_path.stem}_compressed.png"

        output_path = self.compress_dir / output_filename

        # 打开并压缩图片
        img = Image.open(input_path)

        # 获取原图信息
        original_mode = img.mode
        print(f"原图模式: {original_mode}, 尺寸: {img.size}")

        # 压缩保存
        img.save(
            output_path,
            'PNG',
            optimize=True,  # 优化
            compress_level=compress_level  # 压缩级别
        )

        # 计算压缩率
        original_size = input_path.stat().st_size / 1024
        compressed_size = output_path.stat().st_size / 1024
        compression_ratio = (1 - compressed_size / original_size) * 100

        print(f"\n压缩完成:")
        print(f"  原图: {input_path.name} ({original_size:.2f} KB)")
        print(f"  压缩后: {output_path.name} ({compressed_size:.2f} KB)")
        print(f"  压缩率: {compression_ratio:.1f}%")

        return output_path

    def decompress_png(self, compressed_path=None, all_files=False):
        """
        解压（还原）压缩的 PNG 图片到 unzip 文件夹
        注意：PNG 压缩是无损的，这里实际上是复制并可选地取消优化

        Args:
            compressed_path: 指定要解压的压缩文件路径，如果为 None 则使用最新的压缩文件
            all_files: 是否解压所有 compress 文件夹中的文件

        Returns:
            list: 解压后的文件路径列表
        """
        decompressed_files = []

        if all_files:
            # 解压所有 PNG 文件
            png_files = list(self.compress_dir.glob("*.png")) + list(self.compress_dir.glob("*.PNG"))
            if not png_files:
                print(f"在 {self.compress_dir} 中没有找到压缩的 PNG 文件")
                return []

            for png_file in png_files:
                decompressed = self._decompress_single(png_file)
                if decompressed:
                    decompressed_files.append(decompressed)

        elif compressed_path:
            # 解压指定的文件
            compressed_path = Path(compressed_path)
            if not compressed_path.exists():
                raise FileNotFoundError(f"压缩文件不存在: {compressed_path}")

            decompressed = self._decompress_single(compressed_path)
            if decompressed:
                decompressed_files.append(decompressed)

        else:
            # 解压最新的压缩文件
            png_files = list(self.compress_dir.glob("*.png")) + list(self.compress_dir.glob("*.PNG"))
            if not png_files:
                print(f"在 {self.compress_dir} 中没有找到压缩的 PNG 文件")
                return []

            latest_file = max(png_files, key=lambda f: f.stat().st_mtime)
            decompressed = self._decompress_single(latest_file)
            if decompressed:
                decompressed_files.append(decompressed)

        return decompressed_files

    def _decompress_single(self, compressed_file):
        """
        解压单个 PNG 文件（实际是读取并重新保存，去除优化）

        Args:
            compressed_file: 压缩的 PNG 文件路径

        Returns:
            Path: 解压后的文件路径
        """
        # 生成输出文件名
        # 如果文件名包含 _compressed，则移除；否则添加 _decompressed
        if "_compressed" in compressed_file.stem:
            output_filename = compressed_file.stem.replace("_compressed", "") + ".png"
        else:
            output_filename = f"{compressed_file.stem}_decompressed.png"

        output_path = self.unzip_dir / output_filename

        # 读取压缩的 PNG 并重新保存（不使用优化）
        img = Image.open(compressed_file)

        # 重新保存为未优化的 PNG（compress_level=0 表示不压缩）
        img.save(
            output_path,
            'PNG',
            optimize=False,
            compress_level=0  # 不压缩，快速保存
        )

        # 计算文件大小变化
        compressed_size = compressed_file.stat().st_size / 1024
        decompressed_size = output_path.stat().st_size / 1024
        size_increase = (decompressed_size - compressed_size) / compressed_size * 100

        print(f"\n解压完成:")
        print(f"  压缩文件: {compressed_file.name} ({compressed_size:.2f} KB)")
        print(f"  解压后: {output_path.name} ({decompressed_size:.2f} KB)")
        print(f"  体积增加: {size_increase:.1f}%")

        return output_path

    def get_file_info(self, file_path):
        """
        获取文件信息

        Args:
            file_path: 文件路径

        Returns:
            dict: 文件信息字典
        """
        file_path = Path.cwd() / file_path
        # file_path = Path(file_path)
        if not file_path.exists():
            return None

        img = Image.open(file_path)

        return {
            'name': file_path.name,
            'size_kb': file_path.stat().st_size / 1024,
            'dimensions': img.size,
            'mode': img.mode,
            'format': img.format
        }

    def compress_and_decompress_workflow(self, input_path, compress_level=9):
        """
        完整工作流：压缩 -> 解压

        Args:
            input_path: 原始 PNG 图片路径
            compress_level: 压缩级别

        Returns:
            dict: 包含压缩和解压结果的字典
        """
        print("=" * 60)
        print("开始 PNG 图片处理流程")
        print("=" * 60)

        # 1. 显示原始文件信息
        print("\n1. 原始文件信息:")
        original_info = self.get_file_info(input_path)
        if original_info:
            print(f"   文件名: {original_info['name']}")
            print(f"   大小: {original_info['size_kb']:.2f} KB")
            print(f"   尺寸: {original_info['dimensions']}")
            print(f"   模式: {original_info['mode']}")

        # 2. 压缩图片
        print("\n2. 压缩图片:")
        compressed_path = self.compress_png(input_path, compress_level)

        # 3. 显示压缩后信息
        print("\n3. 压缩后文件信息:")
        compressed_info = self.get_file_info(compressed_path)
        if compressed_info:
            print(f"   文件名: {compressed_info['name']}")
            print(f"   大小: {compressed_info['size_kb']:.2f} KB")
            print(f"   尺寸: {compressed_info['dimensions']}")

        # 4. 解压图片
        print("\n4. 解压图片:")
        decompressed_paths = self.decompress_png(compressed_path)

        # 5. 显示解压后信息
        if decompressed_paths:
            print("\n5. 解压后文件信息:")
            decompressed_info = self.get_file_info(decompressed_paths[0])
            if decompressed_info:
                print(f"   文件名: {decompressed_info['name']}")
                print(f"   大小: {decompressed_info['size_kb']:.2f} KB")
                print(f"   尺寸: {decompressed_info['dimensions']}")

        print("\n" + "=" * 60)
        print("处理完成！")
        print(f"压缩文件位置: {self.compress_dir}")
        print(f"解压文件位置: {self.unzip_dir}")
        print("=" * 60)

        return {
            'original': input_path,
            'compressed': compressed_path,
            'decompressed': decompressed_paths[0] if decompressed_paths else None
        }


# 使用示例
if __name__ == "__main__":
    # 初始化工具类
    compressor = PNGCompressor()

    # 方式1：完整工作流（推荐）
    result = compressor.compress_and_decompress_workflow("screenshot_basic_info.png", compress_level=9)

    # 方式2：分步执行
    # compressor = PNGCompressor()
    #
    # # 步骤1：压缩图片
    # compressed_file = compressor.compress_png("example.png", compress_level=9)
    #
    # # 步骤2：解压图片
    # decompressed_files = compressor.decompress_png(compressed_file)

    # 方式3：批量处理
    # compressor = PNGCompressor()
    #
    # # 压缩多个文件
    # for png_file in Path(".").glob("*.png"):
    #     compressor.compress_png(png_file)
    #
    # # 解压所有压缩文件
    # compressor.decompress_png(all_files=True)

    # file_path = "screenshot_basic_info.png"
    # file_path = Path.cwd() / file_path
    # print(f"file_path: {file_path}  {type(file_path)}")