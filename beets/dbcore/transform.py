from abc import ABC
from collections.abc import Sequence

FieldTransformType = type["FieldTransform"]

builtin_transforms: dict[str, FieldTransformType] = {}


def builtin_transform(transform_cls):
    builtin_transforms[transform_cls.name] = transform_cls

    return transform_cls


def union(transforms: Sequence[FieldTransformType], *args, **kwargs):
    if not transforms:
        return Nop()

    if len(transforms) == 1:
        return transforms[0]

    return CollectionFieldTransform(transforms, *args, **kwargs)


class FieldTransform(ABC):
    """Transform a field used in a query.

    Transforms provide a generic and composable way for users to choose how
    queried values are compared.
    """

    def __init__(self, pattern: str):
        self.pattern = pattern

    def apply_to_sql(self, expr: str) -> str:
        """Apply the transform to an SQL column expression.

        The expression should be a valid argument to an SQL function.
        Example: `table.field` or `func(table.field)`
        """
        raise NotImplementedError

    def apply_to_value(self, value: str) -> str:
        """Apply the transform to a Python value."""
        raise NotImplementedError


class Nop(FieldTransform):
    """No-op transform."""

    def __init__(self, pattern: None | str = None):
        super().__init__(pattern)

    def apply_to_sql(self, expr: str) -> str:
        return expr

    def apply_to_value(self, value: str) -> str:
        return value


class CollectionFieldTransform(FieldTransform):
    """A single `FieldTransform` that is composed of multiple sub-transforms.

    Applying the transform applies each sub-transform in the given order.
    """

    def __init__(
        self, subtransforms: Sequence[FieldTransformType], *args, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.subtransforms = [cls(*args, **kwargs) for cls in subtransforms]

    def apply_to_sql(self, expr: str) -> str:
        for t in self.subtransforms:
            expr = t.apply_to_sql(expr)

        return expr

    def apply_to_value(self, value: str) -> str:
        for t in self.subtransforms:
            value = t.apply_to_value(value)

        return value


class ConditionalTransform(FieldTransform):
    """Compare items ignoring case."""

    def apply_to_sql(self, expr: str) -> str:
        if not self.enable:
            return expr

        return self._apply_to_sql(expr)

    def _apply_to_sql(self, expr: str) -> str:
        raise NotImplementedError

    def apply_to_value(self, value: str) -> str:
        if not self.enable:
            return value

        return self._apply_to_value(value)

    def _apply_to_value(self, value: str) -> str:
        raise NotImplementedError


@builtin_transform
class SmartCase(ConditionalTransform):
    """Compare items ignoring case."""

    name = "smart-case"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.enable = self.pattern.islower()

    def _apply_to_sql(self, expr: str) -> str:
        return f"lower({expr})"

    def _apply_to_value(self, value: str) -> str:
        return value.lower()
