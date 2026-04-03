import asyncio
import json
import httpx
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
import os

async def test_crawl4ai_douban_book():
    """
    Test crawl4ai API by crawling a Douban book page and extracting specific fields.
    This uses the Docker API to fetch the HTML, and then uses the local JsonCssExtractionStrategy
    to parse the HTML with the provided schema.
    """
    url = "https://book.douban.com/subject/38237921/"
    
    print(f"Target URL: {url}")
    
    # 1. 从本地文件读取 Schema
    schema_file = "douban_schema.json"
    if not os.path.exists(schema_file):
        print(f"❌ Error: Schema file {schema_file} not found.")
        return
        
    with open(schema_file, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    # 因为豆瓣的简介展开后会显示在 `.intro` 里的一个隐藏的 span 内，
    # 或者直接替换掉原来的文本。为了确保抓取到全部文本，可以尝试调整 selector
    # 例如：div.intro 可能会抓取到未展开的文本，我们可以尝试抓取隐藏的那个 span
    # 豆瓣通常把完整文本放在 class="all hidden" 的 span 里，点击后移除 hidden 类
    
    print(f"\nLoaded Extraction Schema from {schema_file}:")
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    
    # 2. 构造请求 Payload
    # 添加 js_code 来点击“展开全部”按钮，并等待一小段时间让内容加载
    js_click_expand = """
    // 豆瓣的“展开全部”按钮
    const expandBtns = document.querySelectorAll('.a_show_full, a.j.a_show_full');
    expandBtns.forEach(btn => {
        try { btn.click(); } catch(e) {}
    });
    // 确保隐藏的 span 显示出来
    const hiddenSpans = document.querySelectorAll('.all.hidden');
    hiddenSpans.forEach(span => {
        span.classList.remove('hidden');
        span.style.display = 'inline';
    });
    // 隐藏短的 span
    const shortSpans = document.querySelectorAll('.short');
    shortSpans.forEach(span => {
        span.style.display = 'none';
    });
    """
    
    payload = {
        "urls": [url],
        "crawler_config": {
            "headers": {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            },
            "wait_for": "css:#info",
            "js_code": [js_click_expand],
            "delay_before_return_html": 2.0 # 等待 2 秒让展开的内容渲染完毕
        }
    }
    
    endpoint = "http://localhost:11235/crawl"
    
    print(f"\nSending POST request to {endpoint}...")
    
    # 3. 发送请求获取 HTML
    async with httpx.AsyncClient() as client:
        try:
            print("开始抓取豆瓣图书信息 (可能需要几秒钟)...")
            response = await client.post(endpoint, json=payload, timeout=60.0)
            
            if response.status_code != 200:
                print(f"\n❌ Error: HTTP {response.status_code}")
                print(response.text)
                return
                
            data = response.json()
            
            if data.get("success") and data.get("results"):
                result = data["results"][0]
                
                if not result.get("success"):
                    print(f"抓取失败: {result.get('error_message')}")
                    return
                    
                print("\n✅ 成功抓取页面内容！")
                
                html_content = result.get("html", "")
                if not html_content:
                    print("❌ Error: No HTML content returned from crawler.")
                    return
                    
                print(f"获取到 HTML 长度: {len(html_content)}")
                print("\n开始使用 JsonCssExtractionStrategy 进行本地解析...")
                
                # 4. 本地使用 JsonCssExtractionStrategy 解析 HTML
                try:
                    strategy = JsonCssExtractionStrategy(schema)
                    extracted_data = strategy.extract(url, html_content)
                    
                    print("\n" + "="*50)
                    print("🎉 EXTRACTION RESULT:")
                    print("="*50)
                    print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
                    print("="*50)
                    
                except Exception as parse_e:
                    print(f"\n❌ 解析失败: {parse_e}")
                    
            else:
                print("\n❌ Request succeeded but no valid results returned:")
                print(json.dumps(data, indent=2))
                
        except Exception as e:
            print(f"\n❌ Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_crawl4ai_douban_book())


