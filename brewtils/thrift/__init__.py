import os

import thriftpy2

bg_thrift = thriftpy2.load(
    os.path.join(os.path.dirname(__file__), "beergarden.thrift"),
    module_name="bg_thrift",
)
