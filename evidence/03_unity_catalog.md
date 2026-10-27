# 03 Unity Catalog（制約・コメント・タグ・ドメイン）

ドメインはアカウント上限(1000/1000)のため親1本のみ。部門は governed tag の許可値で表現。
カタログにはドメインタグを付けない（継承が剥がせないため）。

### スキーマへのタグ付与
```
schema_name | tag_name | tag_value
finance_core | Brickshouse Food and Beverage | finance
finance_core | brickshouse_department | 財務
finance_mart | Brickshouse Food and Beverage | finance
finance_mart | brickshouse_department | 財務
master_core | Brickshouse Food and Beverage | master
master_mart | Brickshouse Food and Beverage | master
procure_core | Brickshouse Food and Beverage | procurement
procure_core | brickshouse_department | 調達
procure_mart | Brickshouse Food and Beverage | procurement
procure_mart | brickshouse_department | 調達
sales_core | Brickshouse Food and Beverage | sales
sales_core | brickshouse_department | 営業
sales_mart | Brickshouse Food and Beverage | sales
sales_mart | brickshouse_department | 営業
trade_core | Brickshouse Food and Beverage | trade
trade_core | brickshouse_department | 販促
trade_mart | Brickshouse Food and Beverage | trade
trade_mart | brickshouse_department | 販促
xdept_mart | Brickshouse Food and Beverage | cross-department
```

### PK / FK 制約（パイプライン定義で宣言したもの）
```
constraint_type | n
FOREIGN KEY | 53
PRIMARY KEY | 24
```

### silver の列数（ECM の926列が維持されているか）
```
table_schema | tables | columns
finance_core | 6 | 259
master_core | 3 | 108
procure_core | 2 | 98
sales_core | 7 | 249
trade_core | 6 | 212
```

### 列コメントが維持されている例（ECM 由来・値域つき）
```
table_name | column_name | comment
order | channel | Channel through which the order was placed.. Valid values are `retail|foodservice|direct_to_consumer|online|wh
order | order_status | Current lifecycle status of the order.. Valid values are `draft|open|confirmed|fulfilled|cancelled|closed`
order | total_gross_amount | Sum of line item list prices before discounts and taxes.
order | total_net_amount | Final amount after discounts and taxes.
```
