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
Hi @feinfra — can these 4 Discover domains be protected from the unused-domain cleanup?
They are an ongoing CPG demo asset, not a time-boxed project, so there's no end date.

Account: FEVM (05d08df7-ae03-43ad-bbae-14babb530ec0)
Workspace: fevm-serverless-rongzi-cpg-general (7474658774258275)

| tag_key | domain_id |
|---|---|
| Brickshouse Food and Beverage | 755ebf12-1718-4b8c-8eb9-9bc2b3650bea |
| Brickshouse Food and Beverage/営業 | 2e7a6889-45ea-40ef-82a4-57b75bb05269 |
| Brickshouse Food and Beverage/財務 | 7209c1c9-0c34-4c9d-93bd-d039726eddef |
| Brickshouse Food and Beverage/マーケティング | 04be6f8f-405f-4d82-a492-88c9fae8c232 |

Plus the 4 governed tag policies with the same keys — deleting a policy cascades to its
domain.

The parent was deleted on 2026-10-27 00:40:47Z in a sweep of 17 domains (found it in
system.access.audit). No complaint — the account is pinned at the 1000-domain limit and
mine looked abandoned. Recreating the domains takes a minute, but the 22 Discover Pages
inside them are lost with them, and Pages have no public API yet, so recovery is a
30-minute manual bulk import.

They're now non-draft, owner-tagged, 59 UC assets attached, and purpose in the subtitle,
so they shouldn't read as unused anymore. Happy to re-confirm they're still in use
whenever you ask.

If there's a better channel or a Jira type for this, point me at it.
```

## 期限を書かない代わりに入れたもの

恒久例外は通りにくいので、元は「11/15 に自分で消す」と期限を切っていた。
継続して使う資産なので期限は外し、代わりに
**「使用中かどうかは聞かれたら答える」**を入れた。
掃除する側が欲しいのは期限ではなく「生きているかを確認できる相手がいること」なので、
これで同じ役割を果たす。

## 書く上で意識したこと

- **削除した人を責めない。** 上限で詰まった人の掃除であって、悪意ではない。
  責める書き方をすると、以後の協力が得られない
- **自分で手を打ったことを先に書く。** 「守ってください」だけだと優先度が上がらない
- **期限を自分から切る。** 恒久例外は通りにくい。11/15 に自分で消すと明言する
- **占有量を数字で出す。** 4/1000 と 4/3074。小さいことが分かると判断が速い
