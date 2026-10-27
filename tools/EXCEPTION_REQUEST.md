# 例外申請の下書き（#field-infra 投稿用）

## 出し先と順番

| 順 | どこ | 何のため |
|---|---|---|
| 1 | **#field-infra**（`@feinfra` を付ける） | まず相談。ドメイン専用の恒久例外手順は確認できていないので、ここで保護対象にできるか聞く |
| 2 | **FEINFRA Jira（Type: Exception）** | 1で「Jira で」と言われた場合、または記録を残したい場合 |
| 3 | `fe-infra-management` の `*_exceptions.json` に PR | Discover domain が対象サービスに含まれる場合のみ。含まれない見込み |

`#fevm-feedback` でも良いが、削除を実施しているのは FE Infra 側の掃除なので
**#field-infra が本線**。

## 投稿文（英語・そのまま貼れる）

```
Hi @feinfra — requesting an exception (or protection) for 4 Discover domains + their
governed tag policies until 2026-11-15.

**What I need protected**

Account: FEVM (05d08df7-ae03-43ad-bbae-14babb530ec0)
Workspace: fevm-serverless-rongzi-cpg-general (7474658774258275)

| tag_key | domain_id |
|---|---|
| Brickshouse Food and Beverage | 755ebf12-1718-4b8c-8eb9-9bc2b3650bea |
| Brickshouse Food and Beverage/営業 | 2e7a6889-45ea-40ef-82a4-57b75bb05269 |
| Brickshouse Food and Beverage/財務 | 7209c1c9-0c34-4c9d-93bd-d039726eddef |
| Brickshouse Food and Beverage/マーケティング | 04be6f8f-405f-4d82-a492-88c9fae8c232 |

Plus the 4 governed tag policies with the same keys (a domain cannot exist without its
tag policy, and deleting the policy cascades to the domain).

**Why**

This is an FE Bar submission (due 2026-11-15) and a customer demo for CPG accounts in
Japan. The build demonstrates Genie One + the UC ontology: 22 Discover Pages live in
these domains and define the terms where departments disagree ("net sales" means five
different numbers across sales / finance / trade / procurement / marketing).

**What already happened**

My parent domain was deleted on 2026-10-27 00:40:47Z as part of a sweep of 17 domains
in 8 minutes. I found it in system.access.audit. Deleting the parent took the
subdomains with it. I don't think this was anything other than someone freeing slots in
an account that is pinned at the 1000-domain limit — my domains were a draft with no
owner set, so they looked abandoned.

The cost to me isn't the domains (1 minute to recreate). It's that the 22 Pages inside
them are lost, and Pages have no public API yet, so the only way back is a 30-minute
Genie Code bulk import. If that happens the night before the demo I have no recovery
window.

**What I've already done so I'm not just asking you to absorb this**

- Set business_owner_ids / technical_owner_ids so they no longer look ownerless
  (only 465 of 989 domains in this account have an owner set)
- Created them non-draft
- Tagged 59 UC assets into them, so they aren't empty
- Put the purpose and the 2026-11-15 expiry in the subtitle, visible in Discover
- A scheduled job re-creates them within 2 hours if they disappear again

**Duration**

Until 2026-11-15. After that I'll delete all 4 domains and all 4 tag policies myself —
happy to be held to that date. Footprint is 4 of 1000 domains and 4 of 3074 tag policies.

Thanks — and if there's a better channel or a Jira type for this, point me at it and
I'll move it there.
```

## 書く上で意識したこと

- **削除した人を責めない。** 上限で詰まった人の掃除であって、悪意ではない。
  責める書き方をすると、以後の協力が得られない
- **自分で手を打ったことを先に書く。** 「守ってください」だけだと優先度が上がらない
- **期限を自分から切る。** 恒久例外は通りにくい。11/15 に自分で消すと明言する
- **占有量を数字で出す。** 4/1000 と 4/3074。小さいことが分かると判断が速い
