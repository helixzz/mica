import {
  CheckCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  MinusCircleOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Col,
  Divider,
  Drawer,
  Form,
  Grid,
  Input,
  List,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType, TablePaginationConfig } from "antd/es/table";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ColumnSettings, type ColumnOption } from "@/components/ColumnSettings";
import { usePersistedColumns } from "@/hooks/usePersistedColumns";

import { api, type Supplier } from "@/api";
import { downloadCSV } from "@/utils/export";
import { showUndoToast } from "@/utils/undo";
import { MonoId } from '@/components/ui/Mono'

const COLUMN_KEYS = {
  code: "code",
  name: "name",
  tax_number: "tax_number",
  contact_name: "contact_name",
  contact_phone: "contact_phone",
  contact_email: "contact_email",
  is_enabled: "is_enabled",
  actions: "actions",
} as const;

const DEFAULT_VISIBLE: string[] = [
  COLUMN_KEYS.code,
  COLUMN_KEYS.name,
  COLUMN_KEYS.contact_name,
  COLUMN_KEYS.contact_phone,
  COLUMN_KEYS.is_enabled,
  COLUMN_KEYS.actions,
];

export default function SuppliersPage() {
  const { t } = useTranslation();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState<boolean | undefined>(
    undefined,
  );
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null);
  const [form] = Form.useForm();

  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const cols = usePersistedColumns("suppliers-list", DEFAULT_VISIBLE);

  const loadWithParams = (opts: {
    search: string;
    is_enabled: boolean | undefined;
    page_num: number;
    page_size: number;
  }) => {
    setLoading(true);
    api
      .suppliersPaginated({
        search: opts.search || undefined,
        is_enabled: opts.is_enabled,
        page: opts.page_num,
        page_size: opts.page_size,
      })
      .then((res) => {
        setSuppliers(res.items);
        setTotal(res.total);
        setPage(res.page);
        setPageSize(res.page_size);
      })
      .finally(() => setLoading(false));
  };

  const load = useCallback(
    (opts?: { page?: number; pageSize?: number }) => {
      const p = opts?.page ?? page;
      const ps = opts?.pageSize ?? pageSize;
      loadWithParams({
        search: searchText,
        is_enabled: statusFilter,
        page_num: p,
        page_size: ps,
      });
    },
    [page, pageSize, searchText, statusFilter],
  );

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = (value: string) => {
    const searchVal = value || "";
    setSearchText(searchVal);
    setPage(1);
    loadWithParams({
      search: searchVal,
      is_enabled: statusFilter,
      page_num: 1,
      page_size: pageSize,
    });
  };

  const handleStatusFilter = (value: string | undefined) => {
    const isEnabled: boolean | undefined =
      value === undefined || value === "" ? undefined : value === "true";
    setStatusFilter(isEnabled);
    setPage(1);
    setSelectedRowKeys([]);
    loadWithParams({
      search: searchText,
      is_enabled: isEnabled,
      page_num: 1,
      page_size: pageSize,
    });
  };

  const handleTableChange = (pag: TablePaginationConfig) => {
    load({ page: pag.current, pageSize: pag.pageSize });
  };

  const handleBatchEnable = async (enabled: boolean) => {
    try {
      await api.batchUpdateSuppliers({
        ids: selectedRowKeys as string[],
        is_enabled: enabled,
      });
      void message.success(
        enabled ? t("common.enabled") : t("common.disabled"),
      );
      setSelectedRowKeys([]);
      load();
    } catch (e: any) {
      void message.error(
        e?.response?.data?.detail || t("admin.operation_failed"),
      );
    }
  };

  const handleExport = () => {
    const headers = [
      t("supplier.code"),
      t("supplier.name"),
      t("supplier.tax_number"),
      t("field.contact_name"),
      t("field.contact_phone"),
      t("field.contact_email"),
      t("supplier.status"),
    ];
    const data = suppliers.map((s) => [
      s.code,
      s.name,
      s.tax_number || "",
      s.contact_name || "",
      s.contact_phone || "",
      s.contact_email || "",
      s.is_enabled !== false ? t("common.enabled") : t("common.disabled"),
    ]);
    downloadCSV(
      `mica-suppliers-${new Date().toISOString().slice(0, 10)}.csv`,
      headers,
      data,
    );
  };

  const handleSave = async () => {
    try {
      const values = form.getFieldsValue();
      if (editingSupplier) {
        await api.updateSupplier(editingSupplier.id, values);
        void message.success(t("supplier.updated"));
      } else {
        await api.createSupplier(values);
        void message.success(t("message.created"));
      }
      form.resetFields();
      setDrawerOpen(false);
      setEditingSupplier(null);
      load();
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t("error.save_failed"));
    }
  };

  const toggleActive = async (supplier: Supplier) => {
    try {
      await api.updateSupplier(supplier.id, {
        is_enabled: !supplier.is_enabled,
      });
      void message.success(
        supplier.is_enabled ? t("admin.deactivated") : t("common.updated"),
      );
      load();
    } catch (e: any) {
      void message.error(
        e?.response?.data?.detail || t("admin.operation_failed"),
      );
    }
  };

  const handleDelete = (supplier: Supplier) => {
    Modal.confirm({
      title: t("supplier.confirm_delete"),
      okText: t("button.delete"),
      okType: "danger",
      cancelText: t("button.cancel"),
      onOk: async () => {
        try {
          await api.deleteSupplier(supplier.id);
          showUndoToast(
            t("undo.deleted", { item: t("nav.suppliers") }),
            async () => {
              await api.restoreFromRecycleBin("supplier", supplier.id);
              load();
            },
            8000,
          );
          load();
        } catch (e: any) {
          void message.error(
            e?.response?.data?.detail || t("admin.operation_failed"),
          );
        }
      },
    });
  };

  const allColumns: ColumnsType<Supplier> = useMemo(
    () => [
      {
        key: COLUMN_KEYS.code,
        title: t("supplier.code"),
        dataIndex: "code",
        width: 120,
        fixed: "left" as const,
        sorter: (a: Supplier, b: Supplier) => a.code.localeCompare(b.code),
      },
      {
        key: COLUMN_KEYS.name,
        title: t("supplier.name"),
        dataIndex: "name",
        width: 200,
        fixed: "left" as const,
        sorter: (a: Supplier, b: Supplier) => a.name.localeCompare(b.name),
        render: (v: string, r: Supplier) => (
          <Link to={`/suppliers/${r.id}`}>{v}</Link>
        ),
      },
      {
        key: COLUMN_KEYS.tax_number,
        title: t("supplier.tax_number"),
        dataIndex: "tax_number",
        width: 180,
        sorter: (a: Supplier, b: Supplier) =>
          (a.tax_number || "").localeCompare(b.tax_number || ""),
        render: (v: string | null) => v || "-",
      },
      {
        key: COLUMN_KEYS.contact_name,
        title: t("field.contact_name"),
        dataIndex: "contact_name",
        width: 120,
        sorter: (a: Supplier, b: Supplier) =>
          (a.contact_name || "").localeCompare(b.contact_name || ""),
        render: (v: string | null) => v || "-",
      },
      {
        key: COLUMN_KEYS.contact_phone,
        title: t("field.contact_phone"),
        dataIndex: "contact_phone",
        width: 150,
        sorter: (a: Supplier, b: Supplier) =>
          (a.contact_phone || "").localeCompare(b.contact_phone || ""),
        render: (v: string | null) => v || "-",
      },
      {
        key: COLUMN_KEYS.contact_email,
        title: t("field.contact_email"),
        dataIndex: "contact_email",
        width: 200,
        sorter: (a: Supplier, b: Supplier) =>
          (a.contact_email || "").localeCompare(b.contact_email || ""),
        render: (v: string | null) => v || "-",
      },
      {
        key: COLUMN_KEYS.is_enabled,
        title: t("supplier.status"),
        dataIndex: "is_enabled",
        width: 90,
        sorter: (a: Supplier, b: Supplier) =>
          (a.is_enabled ? 1 : 0) - (b.is_enabled ? 1 : 0),
        render: (v: boolean) => (
          <Tag color={v !== false ? "success" : "default"}>
            {v !== false ? t("common.enabled") : t("common.disabled")}
          </Tag>
        ),
      },
      {
        key: COLUMN_KEYS.actions,
        title: t("common.actions"),
        width: 220,
        fixed: "right" as const,
        render: (_: unknown, r: Supplier) => (
          <Space>
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => {
                setEditingSupplier(r);
                form.setFieldsValue(r);
                setDrawerOpen(true);
              }}
            />
            <Button
              size="small"
              danger={r.is_enabled !== false}
              onClick={() => toggleActive(r)}
            >
              {r.is_enabled !== false
                ? t("common.disabled")
                : t("common.enabled")}
            </Button>
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(r)}
            />
          </Space>
        ),
      },
    ],
    [t],
  );

  const columnOptions: ColumnOption[] = useMemo(
    () =>
      allColumns.map((c) => ({
        key: c.key as string,
        label: typeof c.title === "string" ? c.title : (c.key as string),
        alwaysVisible:
          c.key === COLUMN_KEYS.code ||
          c.key === COLUMN_KEYS.name ||
          c.key === COLUMN_KEYS.actions,
      })),
    [allColumns],
  );

  const visibleColumns = useMemo(
    () =>
      allColumns.filter(
        (c) =>
          c.key === COLUMN_KEYS.code ||
          c.key === COLUMN_KEYS.name ||
          c.key === COLUMN_KEYS.actions ||
          cols.isVisible(c.key as string),
      ),
    [allColumns, cols],
  );

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t("supplier.title")}
        </Typography.Title>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>
            {t("button.export_excel")}
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingSupplier(null);
              form.resetFields();
              setDrawerOpen(true);
            }}
          >
            {t("supplier.new")}
          </Button>
          {!isMobile && (
            <ColumnSettings
              options={columnOptions}
              visibleKeys={cols.visibleKeys}
              onToggle={cols.toggle}
              onReset={cols.reset}
            />
          )}
        </Space>
      </div>

      <Row gutter={[12, 12]} align="middle">
        <Col xs={24} md={8} lg={6}>
          <Input.Search
            placeholder={t("search.placeholder")}
            allowClear
            onSearch={handleSearch}
            style={{ width: "100%" }}
          />
        </Col>
        <Col xs={24} md={6} lg={4}>
          <Select
            style={{ width: "100%" }}
            placeholder={t("supplier.status")}
            allowClear
            onChange={handleStatusFilter}
            options={[
              { value: "true", label: t("common.enabled") },
              { value: "false", label: t("common.disabled") },
            ]}
          />
        </Col>
        <Col xs={24} md={10} lg={14}>
          <Space wrap>
            {selectedRowKeys.length > 0 && (
              <>
                <Button
                  size="small"
                  icon={<CheckCircleOutlined />}
                  onClick={() => handleBatchEnable(true)}
                >
                  {t("button.enable_selected")}
                </Button>
                <Button
                  size="small"
                  icon={<MinusCircleOutlined />}
                  onClick={() => handleBatchEnable(false)}
                >
                  {t("button.disable_selected")}
                </Button>
              </>
            )}
            <Typography.Text type="secondary">
              {selectedRowKeys.length > 0
                ? t("common.selected_count", { count: selectedRowKeys.length })
                : `${total} ${t("supplier.count")}`}
            </Typography.Text>
          </Space>
        </Col>
      </Row>

      {isMobile ? (
        <List
          dataSource={suppliers}
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (p, ps) => load({ page: p, pageSize: ps }),
            showTotal: (cnt) => `${cnt} ${t("supplier.count")}`,
          }}
          renderItem={(item) => (
            <List.Item style={{ padding: "12px 0" }}>
              <Card size="small" style={{ width: "100%", borderRadius: 8 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 8,
                  }}
                >
                  <Space>
                    <Link to={`/suppliers/${item.id}`}>
                      <strong>{item.name}</strong>
                    </Link>
                    <Tag><MonoId>{item.code}</MonoId></Tag>
                  </Space>
                  <Tag
                    color={item.is_enabled !== false ? "success" : "default"}
                  >
                    {item.is_enabled !== false
                      ? t("common.enabled")
                      : t("common.disabled")}
                  </Tag>
                </div>

                {(item.contact_name || item.contact_phone) && (
                  <div
                    style={{
                      marginBottom: 4,
                      color: "var(--color-text-secondary)",
                    }}
                  >
                    {item.contact_name || "-"} · {item.contact_phone || "-"}
                  </div>
                )}

                {item.contact_email && (
                  <div style={{ marginBottom: 12 }}>
                    <Typography.Text
                      ellipsis={{ tooltip: true }}
                      type="secondary"
                    >
                      {item.contact_email}
                    </Typography.Text>
                  </div>
                )}

                <div
                  style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    marginTop: 12,
                  }}
                >
                  <Space>
                    <Button
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => {
                        setEditingSupplier(item);
                        form.setFieldsValue(item);
                        setDrawerOpen(true);
                      }}
                    />
                    <Button
                      size="small"
                      danger={item.is_enabled !== false}
                      onClick={() => toggleActive(item)}
                    >
                      {item.is_enabled !== false
                        ? t("common.disabled")
                        : t("common.enabled")}
                    </Button>
                    <Button
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => handleDelete(item)}
                    />
                  </Space>
                </div>
              </Card>
            </List.Item>
          )}
        />
      ) : (
        <Table
          dataSource={suppliers}
          rowKey="id"
          size="small"
          loading={loading}
          rowSelection={rowSelection}
          onChange={handleTableChange}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (cnt) => `${cnt} ${t("supplier.count")}`,
          }}
          columns={visibleColumns}
          scroll={{ x: "max-content" }}
        />
      )}

      <Drawer
        title={
          editingSupplier
            ? t("supplier.edit", { name: editingSupplier.name })
            : t("supplier.new")
        }
        width={420}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setEditingSupplier(null);
        }}
        footer={
          <Space style={{ float: "right" }}>
            <Button
              onClick={() => {
                setDrawerOpen(false);
                setEditingSupplier(null);
              }}
            >
              {t("button.cancel")}
            </Button>
            <Button type="primary" onClick={handleSave}>
              {t("button.save")}
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="code"
            label={t("supplier.code")}
            rules={[{ required: true }]}
          >
            <Input disabled={!!editingSupplier} />
          </Form.Item>
          <Form.Item
            name="name"
            label={t("supplier.name")}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="tax_number" label={t("supplier.tax_number")}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_name" label={t("field.contact_name")}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_phone" label={t("field.contact_phone")}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_email" label={t("field.contact_email")}>
            <Input />
          </Form.Item>
          <Divider
            orientation="left"
            plain
            style={{ fontSize: 13, color: "var(--color-primary-500)" }}
          >
            {t("supplier.payee_section")}
          </Divider>
          <Form.Item
            name="payee_name"
            label={t("supplier.payee_name")}
            help={t("supplier.payee_name_help")}
          >
            <Input placeholder={editingSupplier?.name ?? ""} />
          </Form.Item>
          <Form.Item name="payee_bank" label={t("supplier.payee_bank")}>
            <Input />
          </Form.Item>
          <Form.Item
            name="payee_bank_account"
            label={t("supplier.payee_bank_account")}
          >
            <Input />
          </Form.Item>
          <Form.Item name="notes" label={t("supplier.notes")}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Drawer>
    </Space>
  );
}
