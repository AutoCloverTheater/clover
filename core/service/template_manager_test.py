import unittest
import numpy as np
import cv2
import sys
import os
import json
import shutil
from pathlib import Path
from core.service.template_manager import TemplateManager, TemplateImg


class TestTemplateManager(unittest.TestCase):
    """TemplateManager 类的单元测试"""

    @classmethod
    def setUpClass(cls):
        """测试类启动前的准备工作"""
        print("\n" + "=" * 60)
        print("开始 TemplateManager 测试套件")
        print("=" * 60)

    @classmethod
    def tearDownClass(cls):
        """测试类结束后的清理工作"""
        print("\n" + "=" * 60)
        print("TemplateManager 测试套件完成")
        print("=" * 60)

    def setUp(self):
        """每个测试方法执行前的准备"""
        self.manager = TemplateManager()
        # 创建测试用的临时目录
        self.test_templates_dir = self.manager.templatesDir / "test_temp"
        self.test_templates_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """每个测试方法执行后的清理"""
        # 清理测试生成的文件
        if self.test_templates_dir.exists():
            shutil.rmtree(self.test_templates_dir)

    def create_test_image(self, width=100, height=100, color=None):
        """创建测试用的图像"""
        if color is None:
            # 随机彩色图像
            return np.random.randint(0, 255, (height, width, 3),
                                     dtype=np.uint8)
        else:
            # 指定颜色的图像
            img = np.ones((height, width, 3), dtype=np.uint8) * color
            return img.astype(np.uint8)

    def test_01_save_template_auto_id(self):
        """测试 1: 保存模板（自动生成UUID）"""
        print("\n" + "-" * 50)
        print("测试 1: 保存模板（自动生成UUID）")
        print("-" * 50)

        # 创建测试图像
        test_image = self.create_test_image(100, 100)
        roi = [10, 10, 50, 50]

        # 保存模板
        result = self.manager.save("", "测试模板1", roi, test_image)

        # 验证结果
        self.assertTrue(result, "保存应该成功")
        self.assertTrue(self.manager.jsonFile.exists(), "JSON 文件应该被创建")

        # 验证 JSON 内容
        with open(self.manager.jsonFile, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIn("rois", data, "JSON 应该包含 rois 字段")
        self.assertGreater(len(data["rois"]), 0, "rois 应该至少有一个条目")

        # 获取最新保存的模板 ID
        template_id = list(data["rois"].keys())[-1]
        print(f"✓ 生成的模板 ID: {template_id}")

        # 验证图片文件是否存在
        img_path = self.manager.templatesDir / f"{template_id}.png"
        self.assertTrue(img_path.exists(), f"图片文件应该存在: {img_path}")
        print(f"✓ 图片文件已创建: {img_path.name}")

        print("✓ 测试通过")

    def test_02_save_template_custom_id(self):
        """测试 2: 保存模板（使用自定义ID）"""
        print("\n" + "-" * 50)
        print("测试 2: 保存模板（使用自定义ID）")
        print("-" * 50)

        custom_id = "custom_test_001"
        test_image = self.create_test_image(200, 200, color=(128, 128, 128))
        roi = [50, 50, 100, 100]

        # 保存模板
        result = self.manager.save(custom_id, "自定义ID模板", roi, test_image)

        # 验证结果
        self.assertTrue(result, "保存应该成功")

        # 验证 JSON 中是否存在自定义 ID
        with open(self.manager.jsonFile, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIn(custom_id, data["rois"],
                      f"JSON 应该包含自定义 ID: {custom_id}")
        self.assertEqual(data["rois"][custom_id]["name"], "自定义ID模板")
        self.assertEqual(data["rois"][custom_id]["roi"], roi)

        # 验证图片文件
        img_path = self.manager.templatesDir / f"{custom_id}.png"
        self.assertTrue(img_path.exists(), f"图片文件应该存在: {img_path}")

        print(f"✓ 自定义 ID: {custom_id}")
        print(f"✓ 模板名称: {data['rois'][custom_id]['name']}")
        print("✓ 测试通过")

    def test_03_save_multiple_templates(self):
        """测试 3: 批量保存多个模板"""
        print("\n" + "-" * 50)
        print("测试 3: 批量保存多个模板")
        print("-" * 50)

        template_ids = []

        # 保存 5 个模板
        for i in range(5):
            test_image = self.create_test_image(150, 150)
            roi = [20, 20, 80, 80]

            result = self.manager.save("", f"批量模板_{i + 1}", roi,
                                       test_image)
            self.assertTrue(result, f"模板 {i + 1} 应该保存成功")

            # 获取刚保存的模板 ID
            with open(self.manager.jsonFile, 'r', encoding='utf-8') as f:
                data = json.load(f)
            template_ids.append(list(data["rois"].keys())[-1])

            print(f"✓ 模板 {i + 1} 保存成功, ID: {template_ids[-1][:8]}...")

        # 验证总数
        with open(self.manager.jsonFile, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"\n✓ 总共保存了 {len(data['rois'])} 个模板")
        print("✓ 测试通过")

    def test_04_find_template_by_id(self):
        """测试 4: 根据 ID 查找模板"""
        print("\n" + "-" * 50)
        print("测试 4: 根据 ID 查找模板")
        print("-" * 50)

        # 先保存一个模板
        custom_id = "find_test_001"
        test_image = self.create_test_image(100, 100, color=(200, 100, 50))
        roi = [10, 10, 80, 80]

        self.manager.save(custom_id, "查找测试模板", roi, test_image)

        # 查找模板
        template = self.manager.find_template_by_id(custom_id)

        self.assertIsNotNone(template, "应该能找到模板")
        self.assertIsInstance(template, TemplateImg,
                              "返回的应该是 TemplateImg 对象")
        self.assertIsNotNone(template.img, "模板应该有图像数据")

        print(f"✓ 找到模板: {custom_id}")
        print(f"✓ 图像尺寸: {template.img.shape}")
        print(f"✓ ROI: {template.roi}")

        # 测试查找不存在的 ID
        not_found_template = self.manager.find_template_by_id(
            "non_existent_id")
        self.assertIsNone(not_found_template, "不存在的 ID 应该返回 None")
        print("✓ 不存在的 ID 正确返回 None")
        print("✓ 测试通过")

    def test_05_delete_template(self):
        """测试 5: 删除模板"""
        print("\n" + "-" * 50)
        print("测试 5: 删除模板")
        print("-" * 50)

        # 先保存一个模板
        delete_test_id = "delete_test_005"
        test_image = self.create_test_image(100, 100)
        roi = [10, 10, 80, 80]

        self.manager.save(delete_test_id, "待删除模板", roi, test_image)

        # 验证模板存在
        img_path = self.manager.templatesDir / f"{delete_test_id}.png"
        self.assertTrue(img_path.exists(), "模板文件应该存在")

        # 删除模板
        result = self.manager.delete(delete_test_id)
        self.assertTrue(result, "删除应该成功")

        # 验证模板已被删除
        self.assertFalse(img_path.exists(), "模板文件应该被删除")

        with open(self.manager.jsonFile, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertNotIn(delete_test_id, data["rois"],
                         "JSON 中不应该包含已删除的 ID")

        print(f"✓ 模板 {delete_test_id} 已成功删除")

        # 测试删除不存在的模板
        result_not_exist = self.manager.delete("non_existent_id")
        self.assertTrue(result_not_exist, "删除不存在的模板应该返回 True")
        print("✓ 删除不存在的模板应该返回 True")
        print("✓ 测试通过")

    def test_06_load_png_files(self):
        """测试 6: 加载 PNG 文件列表"""
        print("\n" + "-" * 50)
        print("测试 6: 加载 PNG 文件列表")
        print("-" * 50)

        # 先保存几个模板
        for i in range(3):
            test_image = self.create_test_image(100, 100)
            roi = [10, 10, 80, 80]
            self.manager.save("", f"PNG测试_{i + 1}", roi, test_image)

        # 加载 PNG 文件列表
        png_files = self.manager._load_png_file_from_dir()

        self.assertIsInstance(png_files, list, "应该返回列表")
        self.assertGreater(len(png_files), 0, "应该至少有一个 PNG 文件")

        print(f"✓ 找到 {len(png_files)} 个 PNG 文件:")
        for file in png_files[:5]:  # 只显示前 5 个
            print(f"  - {file}")

        # 验证所有文件都是 .png 格式
        for file in png_files:
            self.assertTrue(file.lower().endswith('.png'),
                            f"文件应该是 PNG 格式: {file}")

        for file in png_files:
            delPath = Path( f"{self.manager.templatesDir}/{file}")
            delPath.unlink()
        self.manager._load_png_file_from_dir()
        print("✓ 测试通过")

    def test_07_save_with_invalid_roi(self):
        """测试 7: 使用无效的 ROI 参数保存"""
        print("\n" + "-" * 50)
        print("测试 7: 使用无效的 ROI 参数保存")
        print("-" * 50)

        test_image = self.create_test_image(100, 100)

        # 测试空 ROI
        invalid_roi = []
        result = self.manager.save("", "无效ROI模板", invalid_roi, test_image)
        print(f"✓ 空 ROI 处理: {'成功' if result else '失败'}")

        # 测试 ROI 长度不为 4
        invalid_roi_2 = [10, 20, 30]
        result2 = self.manager.save("", "无效ROI模板2", invalid_roi_2,
                                    test_image)
        print(f"✓ 非标准 ROI 处理: {'成功' if result2 else '失败'}")

        print("✓ 测试通过")

    def test_08_json_data_integrity(self):
        """测试 8: JSON 数据完整性"""
        print("\n" + "-" * 50)
        print("测试 8: JSON 数据完整性")
        print("-" * 50)

        # 保存多个模板
        test_data = []
        for i in range(3):
            template_id = f"integrity_test_{i:03d}"
            test_image = self.create_test_image(100 + i * 10, 100 + i * 10)
            roi = [10 + i, 10 + i, 80, 80]

            self.manager.save(template_id, f"完整性测试_{i}", roi, test_image)
            test_data.append({
                "id": template_id,
                "name": f"完整性测试_{i}",
                "roi": roi
            })

        # 读取 JSON 并验证
        with open(self.manager.jsonFile, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 验证结构
        self.assertIn("images", data, "JSON 应该包含 images 字段")
        self.assertIn("rois", data, "JSON 应该包含 rois 字段")
        self.assertIsInstance(data["images"], dict, "images 应该是字典")
        self.assertIsInstance(data["rois"], dict, "rois 应该是字典")

        # 验证每个模板的数据
        for item in test_data:
            tid = item["id"]
            self.assertIn(tid, data["rois"], f"应该包含模板: {tid}")
            self.assertEqual(data["rois"][tid]["name"], item["name"])
            self.assertEqual(data["rois"][tid]["roi"], item["roi"])
            self.assertEqual(data["rois"][tid]["id"], tid)

        print(f"✓ JSON 结构完整")
        print(f"✓ 验证了 {len(test_data)} 个模板的数据完整性")
        print("✓ 测试通过")

    def test_09_template_img_class(self):
        """测试 9: TemplateImg 类功能"""
        print("\n" + "-" * 50)
        print("测试 9: TemplateImg 类功能")
        print("-" * 50)

        # 创建一个测试图片文件
        test_img_path = self.test_templates_dir / "test_template.png"
        test_image = self.create_test_image(50, 50, color=(100, 150, 200))
        cv2.imwrite(str(test_img_path), test_image)

        # 从文件路径加载
        template_from_path = TemplateImg(str(test_img_path))
        self.assertIsNotNone(template_from_path.img, "从路径加载应该成功")
        self.assertEqual(template_from_path.img.shape[:2], (50, 50),
                         "图像尺寸应该正确")

        print(f"✓ 从路径加载图像: {test_img_path.name}")
        print(f"✓ 图像尺寸: {template_from_path.img.shape}")

        # 测试设置 ROI
        test_roi = [10, 10, 30, 30]
        template_from_path.set_roi(test_roi)
        self.assertEqual(template_from_path.roi, test_roi,
                         "ROI 应该被正确设置")
        print(f"✓ ROI 设置成功: {template_from_path.roi}")

        # 从字节数据加载
        _, encoded_img = cv2.imencode('.png', test_image)
        img_bytes = encoded_img.tobytes()
        template_from_bytes = TemplateImg(img_bytes)
        self.assertIsNotNone(template_from_bytes.img, "从字节加载应该成功")
        print("✓ 从字节数据加载图像成功")

        print("✓ 测试通过")

    def test_10_edge_cases(self):
        """测试 10: 边界情况"""
        print("\n" + "-" * 50)
        print("测试 10: 边界情况")
        print("-" * 50)

        # 测试空字符串 ID（应该生成 UUID）
        test_image = self.create_test_image(100, 100)
        roi = [10, 10, 80, 80]

        result = self.manager.save("", "空ID模板", roi, test_image)
        self.assertTrue(result, "空 ID 应该生成 UUID 并保存成功")

        with open(self.manager.jsonFile, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 找到刚刚保存的模板（应该是最后一个）
        last_key = list(data["rois"].keys())[-1]
        self.assertNotEqual(last_key, "", "ID 不应该是空字符串")
        print(f"✓ 空 ID 生成了 UUID: {last_key[:8]}...")

        # 测试特殊字符名称
        special_name = "特殊字符模板_@#$%"
        result2 = self.manager.save("", special_name, roi, test_image)
        self.assertTrue(result2, "特殊字符名称应该能正常保存")
        print(f"✓ 特殊字符名称保存成功: {special_name}")

        # 测试大尺寸图像
        large_image = self.create_test_image(1000, 1000)
        result3 = self.manager.save("", "大尺寸模板", roi, large_image)
        self.assertTrue(result3, "大尺寸图像应该能正常保存")
        print("✓ 大尺寸图像保存成功 (1000x1000)")

        print("✓ 测试通过")


class TestTemplateManagerIntegration(unittest.TestCase):
    """TemplateManager 集成测试"""

    def test_full_workflow(self):
        """测试完整工作流程：保存 -> 查找 -> 删除"""
        print("\n" + "-" * 50)
        print("集成测试: 完整工作流程")
        print("-" * 50)

        manager = TemplateManager()

        # 1. 保存模板
        template_id = "workflow_test_001"
        test_image = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        roi = [50, 50, 100, 100]

        save_result = manager.save(template_id, "工作流测试模板", roi,
                                   test_image)
        self.assertTrue(save_result, "保存应该成功")
        print("✓ 步骤 1: 保存模板成功")

        # 2. 查找模板
        template = manager.find_template_by_id(template_id)
        self.assertIsNotNone(template, "应该能找到刚保存的模板")
        print("✓ 步骤 2: 查找模板成功")

        # 3. 验证模板数据
        self.assertIsNotNone(template.img, "模板应该有图像数据")
        print(f"✓ 步骤 3: 验证模板数据成功 (尺寸: {template.img.shape})")

        # 4. 删除模板
        delete_result = manager.delete(template_id)
        self.assertTrue(delete_result, "删除应该成功")
        print("✓ 步骤 4: 删除模板成功")

        # 5. 验证删除
        template_after_delete = manager.find_template_by_id(template_id)
        self.assertIsNone(template_after_delete, "删除后应该找不到模板")
        print("✓ 步骤 5: 验证删除成功")

        print("\n✓ 完整工作流程测试通过")


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
