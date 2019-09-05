# 定义索引类
from haystack import indexes
# 导入模型类
from .models import GoodsSKU, GoodsType


# 指定对于某个类的某些数据建立索引
# 索引类名格式：模型类名+Index
class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    # 索引字段 user_template = True指定根据表中的那些字段建立索引文件的说明放在一个文件
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return GoodsSKU

    def index_queryset(self, using=None):
        return self.get_model().objects.all()


class GoodsTypeIndex(indexes.SearchIndex, indexes.Indexable):
    # 索引字段 user_template = True指定根据表中的那些字段建立索引文件的说明放在一个文件
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return GoodsType

    def index_queryset(self, using=None):
        return self.get_model().objects.all()