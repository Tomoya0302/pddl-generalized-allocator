from dataclasses import dataclass
from typing import Dict, Set

@dataclass
class TypeEnv:
    # type -> set(objects)
    objects_of_type: Dict[str, Set[str]]

    def __init__(self):
        self.objects_of_type = {}

    def add_object(self, obj: str, type_name: str) -> None:
        """オブジェクトを指定された型に追加"""
        if type_name not in self.objects_of_type:
            self.objects_of_type[type_name] = set()
        self.objects_of_type[type_name].add(obj)

    def get_objects(self, type_name: str) -> Set[str]:
        """指定された型のオブジェクト集合を返す"""
        return self.objects_of_type.get(type_name, set())
    
    def get_object_type(self, obj: str) -> str | None:
        """オブジェクトの型を返す（見つからない場合はNone）"""
        for type_name, objects in self.objects_of_type.items():
            if obj in objects:
                return type_name
        return None