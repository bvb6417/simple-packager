import pathlib
import tempfile
import struct
import unittest
from native_icon import render_icon_png, render_text_icon
from emoji_catalog import search_emojis


class UIFeatureTests(unittest.TestCase):
    def test_preview_pixels_equal_final_ico_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder)/'icon.ico'
            render_text_icon('🚀',path)
            data=path.read_bytes()
            size,offset=struct.unpack('<II',data[6+3*16+8:6+4*16])
            self.assertEqual(render_icon_png('🚀',48),data[offset:offset+size])

    def test_keyword_search_chinese_english_and_emoji(self):
        for query,expected in [('火箭','🚀'),('ROCKET','🚀'),('📦','📦'),('猫','🐱'),('保存','💾'),('咖啡','☕')]:
            self.assertIn(expected,[row['emoji'] for row in search_emojis(query)])
        self.assertEqual(search_emojis('不存在的关键词xyz'),[])
        self.assertEqual(search_emojis('火箭','食物与饮料'),[])
        self.assertTrue(search_emojis('火箭 rocket'))
        self.assertIn('❤️',[row['emoji'] for row in search_emojis('爱心','符号与物品')])
        all_emojis=[row['emoji'] for row in search_emojis()]
        self.assertEqual(len(all_emojis),len(set(all_emojis)))


if __name__=='__main__':
    unittest.main(verbosity=2)
