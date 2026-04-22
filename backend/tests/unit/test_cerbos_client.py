import pytest

from app.core.field_authz import FIELD_PERMISSIONS


class TestCerbosClientFallback:
    """When Cerbos is unreachable, cerbos_client falls back to
    the static FIELD_PERMISSIONS dict. These tests verify the
    fallback path produces identical results."""

    @pytest.mark.parametrize(
        "resource,role",
        [
            ("purchase_requisition", "admin"),
            ("purchase_requisition", "finance_auditor"),
            ("purchase_order", "it_buyer"),
            ("purchase_order", "dept_manager"),
            ("payment_record", "it_buyer"),
            ("payment_record", "dept_manager"),
            ("invoice", "it_buyer"),
            ("invoice", "dept_manager"),
        ],
    )
    async def test_fallback_matches_field_permissions(self, resource, role):
        from app.core.cerbos_client import check_field_access

        perms = FIELD_PERMISSIONS.get(resource, {}).get(role, set())
        all_fields_for_resource = set()
        for role_perms in FIELD_PERMISSIONS.get(resource, {}).values():
            all_fields_for_resource.update(role_perms)
        all_fields_for_resource.discard("*")

        if not all_fields_for_resource:
            pytest.skip("no fields defined for resource")

        allowed = await check_field_access(
            principal_id="test-user",
            principal_role=role,
            resource_kind=resource,
            resource_id="fallback-test",
            fields=sorted(all_fields_for_resource),
        )

        if "*" in perms:
            assert allowed == all_fields_for_resource
        else:
            assert allowed == perms

    async def test_unknown_resource_returns_all_fields(self):
        from app.core.cerbos_client import check_field_access

        fields = ["a", "b", "c"]
        allowed = await check_field_access(
            principal_id="x",
            principal_role="admin",
            resource_kind="nonexistent",
            resource_id="x",
            fields=fields,
        )
        assert allowed == set(fields)

    async def test_filter_dict_via_cerbos_returns_subset(self):
        from app.core.cerbos_client import filter_dict_via_cerbos

        data = {
            "id": "123",
            "po_number": "PO-001",
            "source_type": "manual",
            "source_ref": "REF-X",
            "created_by_id": "user-999",
            "status": "pending",
        }
        filtered = await filter_dict_via_cerbos(
            data,
            principal_id="bob",
            principal_role="dept_manager",
            resource_kind="purchase_order",
            resource_id="test-po",
        )
        assert "id" in filtered
        assert "po_number" in filtered
        assert "status" in filtered
        assert "source_type" not in filtered
        assert "source_ref" not in filtered
        assert "created_by_id" not in filtered
