# language: zh-TW
Feature: 網頁擷取工具（Web Fetch Tool）
  作為 Agent
  我想要擷取網頁內容並轉換為可讀文字
  以便查閱線上文件或探索網站結構

  Rule: URL 驗證應確保安全性

    Scenario: 合法的 http/https URL 應通過
      When 驗證 "https://example.com"
      Then 應通過驗證並回傳原始 URL

    Scenario: file:// scheme 應被拒絕
      When 驗證 "file:///etc/passwd"
      Then 應拋出不支援的 scheme 錯誤

    Scenario: ftp:// scheme 應被拒絕
      When 驗證 "ftp://example.com/file"
      Then 應拋出不支援的 scheme 錯誤

    Scenario: localhost 預設應被封鎖
      When 驗證 "http://localhost:8080"
      Then 應拋出主機被封鎖的錯誤

    Scenario: 127.0.0.1 預設應被封鎖
      When 驗證 "http://127.0.0.1:3000"
      Then 應拋出主機被封鎖的錯誤

    Scenario: AWS metadata IP 應被封鎖
      When 驗證 "http://169.254.169.254/latest/meta-data/"
      Then 應拋出主機被封鎖的錯誤

    Scenario: 私有 IP 應被封鎖
      When 驗證 "http://192.168.1.1"
      Then 應拋出私有 IP 錯誤

    Scenario: allowed_hosts 可覆蓋封鎖
      When 驗證 "http://127.0.0.1:8080" 且 allowed_hosts 包含 "127.0.0.1"
      Then 應通過驗證

    Scenario: 含帳密的 URL 應被拒絕
      When 驗證 "http://user:pass@example.com"
      Then 應拋出不允許帳密的錯誤

    Scenario: 空主機名稱應被拒絕
      When 驗證 "http://"
      Then 應拋出缺少主機名稱的錯誤

  Rule: HTML 提取應正確轉換內容

    Scenario: 基本段落應正確提取
      Given HTML 為 "<html><body><p>Hello World</p></body></html>"
      When 執行 extract_text
      Then 純文字應包含 "Hello World"

    Scenario: 頁面標題應被提取
      Given HTML 的 title 標籤為 "我的頁面"
      When 執行 extract_text
      Then title 應為 "我的頁面"

    Scenario: script 標籤內容應被移除
      Given HTML 包含 script 標籤與 alert 程式碼
      When 執行 extract_text
      Then 純文字不應包含 "alert"
      And 純文字應包含其他正常文字

    Scenario: style 標籤內容應被移除
      Given HTML 包含 style 標籤與 CSS 樣式
      When 執行 extract_text
      Then 純文字不應包含 "color"
      And 純文字應包含其他正常內容

    Scenario: 連結應被正確提取
      Given HTML 包含兩個 a 標籤（一個相對路徑、一個絕對路徑）
      And base_url 為 "http://localhost:8080"
      When 執行 extract_text
      Then links 應有 2 個項目
      And 第一個連結的 href 應用 base_url 解析為絕對路徑

    Scenario: 相對連結應用 base_url 解析
      Given HTML 包含 '<a href="/page2">下一頁</a>'
      And base_url 為 "http://localhost:3000/page1"
      When 執行 extract_text
      Then 連結的 href 應為 "http://localhost:3000/page2"

    Scenario: 嵌套結構應正確處理
      Given HTML 包含嵌套的 div、h1、p、ul/li 結構
      When 執行 extract_text
      Then 純文字應包含所有層級的文字內容

    Scenario: 空 HTML 應回傳空結果
      Given HTML 為空字串
      When 執行 extract_text
      Then text 應為空、title 應為空、links 應為空列表

  Rule: 應能擷取本地伺服器的網頁內容

    Background:
      Given 本地 HTTP 伺服器已啟動
      And allowed_hosts 包含 "127.0.0.1"

    Scenario: 成功擷取 HTML 頁面
      When Agent 擷取首頁
      Then status_code 應為 200
      And title 應為 "首頁"
      And content_text 應包含 "歡迎"
      And links 應包含至少一個連結

    Scenario: 擷取純文字回應
      When Agent 擷取 /plain 路徑
      Then status_code 應為 200
      And content_text 應為 "純文字內容"
      And links 應為空列表

    Scenario: 404 頁面應回傳狀態碼
      When Agent 擷取不存在的路徑
      Then status_code 應為 404

    Scenario: 超過大小限制應回傳錯誤
      When Agent 擷取 /large 路徑（回應超過 1MB）
      Then 結果應包含 error
      And error 應包含 "過大"

    Scenario: 未允許的 localhost 應回傳錯誤
      Given allowed_hosts 未設定
      When Agent 擷取本地伺服器頁面
      Then 結果應包含 error
      And error 應包含 "封鎖"

    Scenario: 連線失敗應回傳錯誤
      When Agent 擷取一個無法連線的位址
      Then 結果應包含 error
