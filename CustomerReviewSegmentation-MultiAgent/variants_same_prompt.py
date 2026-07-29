# test_fetch.py
from db_utils_pg import get_examples_by_topic_pg
print(get_examples_by_topic_pg("support", 3))
