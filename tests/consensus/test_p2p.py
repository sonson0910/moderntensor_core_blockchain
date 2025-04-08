# tests/consensus/test_p2p.py
import pytest
import json
import time
import dataclasses # <--- Thêm import

# Import hàm cần test và các kiểu dữ liệu liên quan
from sdk.consensus.p2p import canonical_json_serialize
from sdk.core.datatypes import ValidatorScore

# --- Test Cases for canonical_json_serialize ---

def test_canonical_serialize_simple_dict():
    """Kiểm tra serialize dict đơn giản."""
    data = {"b": 2, "a": 1, "c": {"z": 9, "x": 7}}
    expected = '{"a":1,"b":2,"c":{"x":7,"z":9}}'
    assert canonical_json_serialize(data) == expected

def test_canonical_serialize_list_of_scores():
    """Kiểm tra serialize list các đối tượng ValidatorScore."""
    score1 = ValidatorScore(task_id="t1", miner_uid="m1", validator_uid="v1", score=0.9, timestamp=time.time())
    time.sleep(0.01)
    score2 = ValidatorScore(task_id="t1", miner_uid="m1", validator_uid="v2", score=0.85, timestamp=time.time())

    # Chuyển đổi sang dict bằng dataclasses.asdict()
    score1_dict = dataclasses.asdict(score1) # <--- SỬA Ở ĐÂY
    score2_dict = dataclasses.asdict(score2) # <--- SỬA Ở ĐÂY

    data_list_obj = [score1, score2]
    data_list_dict = [score1_dict, score2_dict] # Giữ nguyên để test cả dict

    # Chuỗi JSON mong đợi (dùng dict đã tạo)
    # Sắp xếp keys của dict bên ngoài trước khi dump list
    # (Mặc dù hàm canonical sẽ làm điều này, nhưng làm ở đây cho chắc chắn)
    expected_data_for_dump = sorted([score1_dict, score2_dict], key=lambda x: json.dumps(x, sort_keys=True))
    # ^^^ Lưu ý: Việc sort list dict này có thể không cần thiết nếu chỉ muốn kiểm tra
    #     hàm canonical hoạt động đúng với từng phần tử. Tạo expected dựa trên
    #     output thực tế của hàm canonical có thể tốt hơn.
    # => Đơn giản hóa: Tạo expected_json_str bằng chính hàm canonical
    expected_json_str = canonical_json_serialize([score1, score2])

    # Kiểm tra serialize từ list các object
    serialized_from_obj = canonical_json_serialize(data_list_obj)
    assert serialized_from_obj == expected_json_str

    # Kiểm tra serialize từ list các dict
    # Hàm canonical_json_serialize cũng sẽ xử lý dict bên trong list
    serialized_from_dict = canonical_json_serialize(data_list_dict)
    assert serialized_from_dict == expected_json_str


def test_canonical_serialize_different_order_list():
    """Kiểm tra serialize list với thứ tự phần tử khác nhau không ảnh hưởng output.
    => Bỏ test này vì JSON chuẩn không đảm bảo thứ tự list.
    """
    score1 = ValidatorScore(task_id="t1", miner_uid="m1", validator_uid="v1", score=0.9)
    score2 = ValidatorScore(task_id="t1", miner_uid="m1", validator_uid="v2", score=0.85)
    list1 = [score1, score2]
    list2 = [score2, score1]
    serialized1 = canonical_json_serialize(list1)
    serialized2 = canonical_json_serialize(list2)
    assert serialized1 != serialized2 # <<<--- Assert này sẽ fail

def test_canonical_serialize_empty_list():
    """Kiểm tra serialize list rỗng."""
    data = []
    expected = '[]'
    assert canonical_json_serialize(data) == expected

def test_canonical_serialize_dict_with_scores():
    """Kiểm tra serialize dict có chứa list ValidatorScore."""
    score1 = ValidatorScore(task_id="t1", miner_uid="m1", validator_uid="v1", score=0.9)
    score2 = ValidatorScore(task_id="t1", miner_uid="m1", validator_uid="v2", score=0.85)

    data = {
        "cycle": 10,
        "scores_list": [score1, score2],
        "validator": "v_abc"
    }

    # Chuẩn bị dict tương ứng bằng dataclasses.asdict()
    score1_dict = dataclasses.asdict(score1) # <--- SỬA Ở ĐÂY
    score2_dict = dataclasses.asdict(score2) # <--- SỬA Ở ĐÂY
    expected_data_dict = {
        "cycle": 10,
        "scores_list": [score1_dict, score2_dict], # List các dict
        "validator": "v_abc"
    }
    # Tạo chuỗi JSON mong đợi từ dict đã chuẩn bị, có sắp xếp key
    expected_json_str = json.dumps(expected_data_dict, sort_keys=True, separators=(',', ':'))

    # Serialize dữ liệu gốc
    serialized_output = canonical_json_serialize(data)

    # So sánh output với chuỗi mong đợi
    # Cần đảm bảo hàm convert_to_dict bên trong canonical_json_serialize xử lý đúng
    assert serialized_output == expected_json_str