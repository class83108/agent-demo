# language: zh-TW
Feature: 可恢復串流（Resumable Stream）
  作為開發者
  我想要在客戶端斷線後能恢復串流
  以便不遺失任何 Agent 回應內容

  Background:
    Given Agent 已初始化

  Rule: EventStore 應持久化串流事件

    Scenario: 事件寫入與讀取
      Given 一個空的 MemoryEventStore
      When 寫入 3 個串流事件到同一個 key
      Then 應可讀取到 3 個事件
      And 事件順序應與寫入一致
      And 每個事件應有唯一的遞增 id

    Scenario: 從指定位置讀取事件（offset）
      Given MemoryEventStore 中某 key 有 5 個事件
      When 從第 3 個事件的 id 之後開始讀取
      Then 應只回傳後 2 個事件

    Scenario: 查詢串流狀態為 generating
      Given 已對某 key 寫入事件但尚未標記完成
      When 查詢該 key 的狀態
      Then 狀態應為 "generating"
      And 事件數量應正確

    Scenario: 標記串流完成
      Given 一個進行中的串流
      When 標記該串流為 completed
      Then 查詢狀態應為 "completed"

    Scenario: 標記串流失敗
      Given 一個進行中的串流
      When 標記該串流為 failed
      Then 查詢狀態應為 "failed"

  Rule: MemoryEventStore 應支援 TTL 過期

    Scenario: 過期串流自動清除
      Given MemoryEventStore TTL 設定為極短時間
      And 某 key 中已有事件
      When 等待超過 TTL 時間後查詢
      Then 該串流狀態應為 None
      And 讀取該串流事件應回傳空列表

  Rule: Agent 配置 EventStore 時應自動寫入事件

    Scenario: Agent 串流時自動寫入事件到 EventStore
      Given Agent 配置了 EventStore
      And 呼叫端傳入 stream_id（通常為 session_id）
      When 使用者傳送訊息並完成串流
      Then EventStore 應收到一個或多個 token 類型的事件
      And EventStore 應收到 done 類型的事件
      And 串流狀態應為 completed

    Scenario: 未配置 EventStore 的 Agent 行為不變
      Given Agent 未配置 EventStore
      When 使用者傳送訊息並完成串流
      Then 串流行為應與原本完全相同
      And 不會有任何事件寫入

    Scenario: 未傳入 stream_id 時不寫入 EventStore
      Given Agent 配置了 EventStore
      But 呼叫端未傳入 stream_id
      When 使用者傳送訊息並完成串流
      Then EventStore 不應有任何事件
      And 串流行為應與原本完全相同

  Rule: 客戶端應可從斷點恢復串流

    Scenario: 用 session_id 從 EventStore 讀取已完成串流的所有事件
      Given Agent 已完成一次含 EventStore 的串流
      When 使用同一個 session_id 從 EventStore 讀取所有事件
      Then 應取得完整的事件序列（tokens → done）

    Scenario: 從指定 offset 恢復已完成的串流
      Given Agent 已完成一次含 EventStore 的串流
      And 客戶端只收到前 N 個事件
      When 使用最後收到的 event_id 作為 offset 讀取
      Then 應只回傳該 event_id 之後的事件
      And 不應遺漏任何事件
      And 不應重複任何事件

    Scenario: token 事件拼接應還原完整回應
      Given Agent 已完成一次含 EventStore 的串流
      When 從 EventStore 讀取所有 token 事件並拼接 data
      Then 結果應等於串流收到的完整回應文字
