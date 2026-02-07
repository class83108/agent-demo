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
