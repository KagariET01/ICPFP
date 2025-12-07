#	期末專案：ChatGPT 摘要生成器

##	前置作業

請先安裝 `Docker 28.2.2` 以及 `Python 3.12.3`，另外，建議在 Linux 環境下執行。

1.	安裝 `Docker 28.2.2` 或以上版本，詳情請自己上網找教學。
1.	安裝 `Python 3.12.3` 或以上版本，詳情請自己上網找教學。
1.	如果你想免費提供 OpenAI API Key，請接著看接下來的教學。
	若不想，可直接跳過這些步驟
	1.	到 [OpenAI API Key](https://platform.openai.com/api-keys)
	1.	點右上角 `Create new secret key` 按鈕
	1.	`Owned by` 選 `You`
	1.	`Name` 隨便取
	1.	`Project` 選 `Default project`
	1.	`Permissions` 選 `All`
	1.	點 `Create secret key` 按鈕
	1.	點 `Copy` 按鈕，將 API Key 複製起來，接著放到一個安全的地方
1.	上 [Discord Developer](https://discord.com/developers/applications) 建立一個新的應用程式
	1.	點右上角 `New Application` 按鈕
	1.	`App Name` 隨便取
	1.	點 `Create` 按鈕
	1.	點左側選單的 `Bot`
	1.	點 `Reset Token` 按鈕，然後點 `Yes, do it!` 按鈕
	1.	點 `Copy` 按鈕，將 Bot Token 複製起來，接著放到一個安全的地方
	1.	往下捲，開啟 `Presence Intent`, `Server Members Intent` 以及 `Message Content Intent`
	1.	點 `Save Changes` 按鈕
1.	將你的 Bot 加入你的 Discord 伺服器
	1.	點左側選單的 `OAuth2`，然後點 `URL Generator`
	1.	在 `SCOPES` 區塊，勾選 `bot` 和 `applications.commands`
	1.	在 `BOT PERMISSIONS` 區塊，勾選 `Send Messages`, `Read Message History`, `Use Slash Commands`
	1.	將下方產生的 URL 複製起來，然後貼到瀏覽器開啟
	1.	將 Bot 加入你的 Discord 伺服器
1.	你可以修改 `config.json` 來個人化你的 Bot
	-	(root) `object`
		-	`update_timewait` `number`：設定 Discord Bot 更新 ChatGPT 回應的時間間隔，單位為毫秒，預設值為 `1000`  
			設定太短會導致 Discord API 限制、網路阻塞等問題  
			設定太長會讓使用者以為 Bot 沒有反應
		-	`model` `string` 要使用的 ChatGPT 模型，預設值為 `gpt-3.5-turbo`  
			可選擇的模型請參考 [OpenAI 官方文件](https://platform.openai.com/docs/models)
		-	`admin_id` `DC.User.ID[]`:管理員的 Discord ID 清單，但目前沒什麼作用
		-	`max_len` `number(string)`:Discord 機器人的最大回覆長度，超過這個長度會被截成多則留言，預設值為 `1500`
		-	`log_channel_id` `DC.Channel.ID(string)`:用來記錄除錯日誌的 Discord 頻道 ID
1.	在終端機執行以下指令
	```bash
	python3 main.py
	```
	1.	根據指示輸入你的 OpenAI API Key 以及 Discord Bot Token
		如果你不想提供 OpenAI API Key，可以直接按按 Enter 跳過
	1.	程式會自動建立 `config.json` 檔案，並將你的 API Key 以及 Bot Token 寫入，並自動執行 Docker 容器
1.	到你的 Discord 伺服器，測試你的 Bot 是否能正常運作

##	指令列表

-	`/askai` `question:<string>`：向 ChatGPT 提問，Bot 會回覆 ChatGPT 的回答
-	`/readhtml` `url:<string>`：讀取指定的網頁內容，並將內容摘要後回覆給使用者
-	`/set_token`:會跳出表單，讓使用者輸入 OpenAI API Key，並將其綁定到使用者的 Discord ID 上
-	`/testlongreply`:用來測試長回覆的指令，Bot 會回覆一段很長的文字
-	`/webconculusion` `url:<string>`：讀取指定的網頁內容，並將內容進行結論式摘要後回覆給使用者
