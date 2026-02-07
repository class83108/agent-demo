# language: zh-TW
Feature: Session 後端抽象
  作為開發者
  我想要可抽換的 Session 後端
  以便在不同環境使用不同的儲存方式

  Rule: 記憶體後端應支援基本操作

    Scenario: 儲存並讀取對話歷史
      Given 使用 MemorySessionBackend
      When 儲存一段對話歷史到 session "abc"
      And 讀取 session "abc" 的歷史
      Then 應回傳相同的對話歷史

    Scenario: 讀取不存在的 session
      Given 使用 MemorySessionBackend
      When 讀取 session "not-exist" 的歷史
      Then 應回傳空列表

    Scenario: 重設 session
      Given 使用 MemorySessionBackend
      And session "abc" 已有對話歷史
      When 重設 session "abc"
      Then 讀取 session "abc" 應回傳空列表

  Rule: Redis 後端應支援持久化

    Scenario: 對話歷史應有 TTL
      Given 使用 RedisSessionBackend 且 TTL 為 86400
      When 儲存一段對話歷史
      Then Redis key 的 TTL 應為 86400 秒

  Rule: SQLite 後端應支援基本 CRUD 操作

    Scenario: 儲存並讀取對話歷史
      Given 使用 SQLiteSessionBackend
      When 儲存一段對話歷史到 session "abc"
      And 讀取 session "abc" 的歷史
      Then 應回傳相同的對話歷史

    Scenario: 讀取不存在的 session
      Given 使用 SQLiteSessionBackend
      When 讀取 session "not-exist" 的歷史
      Then 應回傳空列表

    Scenario: 重設 session
      Given 使用 SQLiteSessionBackend
      And session "abc" 已有對話歷史
      When 重設 session "abc"
      Then 讀取 session "abc" 應回傳空列表

  Rule: SQLite 後端應跨程序存活

    Scenario: 關閉後重新開啟仍保留資料
      Given 使用 SQLiteSessionBackend 且指定資料庫檔案路徑
      And 已儲存一段對話歷史到 session "abc"
      When 關閉 backend 並以同一路徑重新建立
      And 讀取 session "abc" 的歷史
      Then 應回傳先前儲存的對話歷史

  Rule: SQLite 後端應支援多 session 隔離

    Scenario: 不同 session 的資料互不影響
      Given 使用 SQLiteSessionBackend
      When 儲存不同對話到 session "s1" 與 session "s2"
      Then 讀取 session "s1" 應只回傳 "s1" 的對話
      And 讀取 session "s2" 應只回傳 "s2" 的對話

    Scenario: 重設單一 session 不影響其他
      Given 使用 SQLiteSessionBackend
      And session "s1" 與 session "s2" 皆有對話歷史
      When 重設 session "s1"
      Then 讀取 session "s1" 應回傳空列表
      And 讀取 session "s2" 應仍有資料

  Rule: SQLite 後端應正確序列化複雜訊息結構

    Scenario: 儲存包含 tool_use 與 tool_result 的對話
      Given 使用 SQLiteSessionBackend
      When 儲存包含工具調用區塊的對話歷史
      And 讀取該 session 的歷史
      Then 工具調用區塊應完整保留（含 type、id、name、input）
      And 工具結果區塊應完整保留（含 tool_use_id、content、is_error）
