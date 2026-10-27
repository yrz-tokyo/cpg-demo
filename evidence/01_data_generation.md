# 01 合成データ生成

生成器: 02_data/generate.py + business.py（stdlib のみ・SEED 固定で決定論）
列の値域は業界データモデル(ECM)の列コメント `Valid values are ...` から取得（自作していない）

### 生成結果
```
finance_core.gl_account                   60 行 x  43 列         7 KB
procure_core.supplier                     80 行 x  48 列        10 KB
master_core.sku                          300 行 x  55 列        42 KB
master_core.category                      24 行 x  20 列         2 KB
finance_core.cost_center                  40 行 x  44 列         7 KB
finance_core.profit_center                20 行 x  42 列         3 KB
master_core.product_standard_cost        300 行 x  33 列        25 KB
sales_core.rep                            60 行 x  33 列         6 KB
sales_core.territory                      12 行 x  25 列         1 KB
sales_core.account                       150 行 x  36 列        13 KB
trade_core.promotion_event               400 行 x  46 列        56 KB
sales_core.order                      24,000 行 x  47 列      2698 KB
procure_core.purchase_order            8,000 行 x  50 列       997 KB
sales_core.invoice                    22,000 行 x  45 列      2672 KB
sales_core.pos_transaction            80,000 行 x  35 列      5322 KB
sales_core.distribution_point          2,400 行 x  28 列       152 KB
finance_core.ar_invoice               22,000 行 x  44 列      2696 KB
finance_core.ap_invoice                8,000 行 x  44 列       857 KB
finance_core.finance_standard_cost       300 行 x  42 列        34 KB
trade_core.promotion_line              4,000 行 x  40 列       452 KB
trade_core.settlement                  1,800 行 x  31 列       153 KB
trade_core.fund                           30 行 x  27 列         3 KB
trade_core.accrual                     4,000 行 x  24 列       259 KB
trade_core.deduction                   5,000 行 x  44 列       616 KB
合計                                   182,976 行
```

### Volume 上の着地（フィード単位ディレクトリ）
```
nielsen__sales_core__distribution_point
pos_edi852__sales_core__pos_transaction
salesforce__sales_core__account
salesforce__sales_core__territory
sap_co__finance_core__cost_center
sap_co__finance_core__finance_standard_cost
sap_co__finance_core__profit_center
sap_co__master_core__product_standard_cost
sap_fi__finance_core__ap_invoice
sap_fi__finance_core__ar_invoice
sap_fi__finance_core__gl_account
sap_mm__master_core__category
sap_mm__master_core__sku
sap_mm__procure_core__purchase_order
sap_mm__procure_core__supplier
sap_sd__sales_core__invoice
sap_sd__sales_core__order
tpm__trade_core__accrual
tpm__trade_core__deduction
tpm__trade_core__fund
tpm__trade_core__promotion_event
tpm__trade_core__promotion_line
tpm__trade_core__settlement
workday__sales_core__rep

```
