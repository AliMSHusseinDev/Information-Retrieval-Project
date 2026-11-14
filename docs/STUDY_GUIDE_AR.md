# دليل مذاكرة Lumen IR — بالمصري

## الفكرة كلها في دقيقة

إحنا عندنا 10 ملفات عن Technology. عايزين ندور على **phrase كاملة** زي
`machine learning`، ونجيب الملفات اللي فيها الكلام بنفس الترتيب وورا بعض.
بعد كده نرتّب الملفات حسب `Cosine Similarity`. المشروع فيه جزئين منفصلين:

1. **Preprocessing:** Spark يبني `Positional Index`، وPython يحسب المصفوفات
   ويحفظها في `outputs/`.
2. **Interactive search:** Flask يقرأ النتائج المحفوظة، والواجهة تبعت query
   وتعرض الملفات والدرجات. مش بنشغّل Spark مع كل search.

الداتا الأصلية فيها **10 documents، 27 unique terms، 64 tokens**.
كلمة `and` في d5 كلمة عادية، مش Boolean operator جوّه الملف.

## Spark وPySpark وFlask بيعملوا إيه؟

**Apache Spark** محرّك معالجة بيانات. **PySpark** هو الـ Python interface
بتاعه. إحنا فعلاً بنقرأ الملفات بـ `wholeTextFiles`، ونطلع occurrence records
بـ `flatMap`، ونجمع positions بـ `groupByKey`. بنستخدم `local[2]`، يعني worker
threads محلية؛ مش لازم cluster عشان نستخدم Spark فعلي.

**Flask** هو web backend. بيقدّم HTML pages وJSON APIs. لما تضغط Search،
JavaScript بيستخدم `fetch('/api/search', ...)` ويبعت JSON. Flask ينادي
`search()` ويرجّع النتائج. JavaScript يعرضها ويحط البيانات في Chart.js.
الحسابات مش بتتعمل بشكل مزيف في الواجهة.

## خريطة الملفات

| الملف | مسؤوليته |
|---|---|
| `data/d1.txt` لحد `d10.txt` | النصوص الأصلية من الورقة |
| `src/indexing.py` | Spark positions، قراءة الملفات، وfingerprint |
| `src/calculations.py` | كل formulas بتاعة collection وquery |
| `src/queries.py` | phrase matching، Boolean filtering، ranking |
| `src/exports.py` | كتابة JSON وCSV من النتائج المحسوبة |
| `src/storage.py` | تحميل model والتأكد إنه مش قديم |
| `run_spark.py` | نقطة تشغيل preprocessing كلها |
| `app.py` | الصفحات والـ APIs والتنزيلات |
| `launcher.py` | تشغيل Waitress، فتح browser، ومنع duplicate launch |
| `templates/` | شكل الصفحات الستة والـ shared shell |
| `static/css/style.css` | الألوان والمسافات والـ responsive layout |
| `static/js/main.js` | التعامل مع controls وعرض بيانات الـ backend |
| `static/js/charts.js` | رسم charts محلية ببيانات حقيقية |
| `outputs/` | كل مخرجات التسليم |
| `tests/reference.py` | قيم مرجعية مستقلة من الـ PDF للاختبار فقط |
| `validate.py` | اختبارات formulas وroutes وexports وcache |
| `tests/browser_smoke.py` | تجربة controls حقيقية بالـ browser |
| `Launch_IR.bat` | double-click launch على Windows |
| `build_exe.bat` | بناء executable على Windows |

## أهم functions — اشرح كل واحدة بإيه؟

### `src/indexing.py`

- `document_number(document_id)`: بتاخد `d10` وترجّع 10 عشان الترتيب يبقى
  d1، d2، ...، d10، مش d1، d10، d2.
- `read_documents(data_dir)`: بتقرأ ملفات `d<number>.txt` وترجّع dictionary
  من document ID للنص. مش بتغيّر ترتيب الكلمات ولا spelling.
- `dataset_fingerprint(data_dir)`: بتحسب SHA-256 من أسماء الملفات والـ bytes.
  ده يكشف أي تغيير في الداتا قبل ما نستخدم outputs قديمة.
- `emit_positions(file_record)`: Spark worker بياخد filename وtext، يعمل
  lowercase وsplit، ويطلع `((term, doc), position)` لكل كلمة بدايةً من 1.
- `build_index(data_dir, master)`: يشغّل Spark، يقرأ ويجمع positions، ويرجّع
  `term → doc → positions` مع Spark version. بيقفل Spark في `finally`.

### `src/calculations.py`

- `weighted_tf(frequency)`: لو count أكبر من صفر يحسب `1 + log10(count)`؛
  لو صفر يرجّع صفر. ده يقلل المبالغة في تأثير التكرار.
- `calculate_collection(index, documents)`: مدخلاته الـ index الحقيقي والملفات؛
  ناتجه كل matrices والـ lengths. بيعد positions، يحسب DF/IDF، يضرب TF-IDF،
  يحسب L2 norm، وبعدين يقسم كل component على طول الـ document.
- `query_vector(tokens, collection_idf)`: يعد الكلمات في الـ query نفسها،
  ويستخدم collection IDF الموجود، ويعمل normalization. بيرجّع tokens وrows
  والـ length. مش بيحسب IDF جديد من query صغيرة.

### `src/queries.py`

- `clean_phrase(value, label)`: يتأكد إن المدخل string مش فاضي وفي الحدود،
  وبعدين lowercase وsplit. بيرجّع tokens أو validation error.
- `phrase_matches(index, tokens)`: يجيب الملفات المشتركة بين الكلمات، ويجرّب
  starts اللي تحقق `position = start + offset` لكل token. الناتج كل starting
  positions والـ ranges لكل ملف. مفيش substring shortcut.
- `search(model, phrase, mode, other)`: يجيب phrase sets، يعمل intersection
  أو difference حسب mode، يبني positive query vector، يحسب dot product لكل
  document، ويرتّب descending. بيرجّع contributions كمان عشان تشرح الدرجة.

### `src/exports.py` و`src/storage.py`

- `write_csv(path, headers, rows)`: يكتب header وrows حقيقية من غير rounding.
- `write_json(path, data)`: يكتب structured data بشكل مقروء وUTF-8.
- `export_all(model, output_dir)`: يحفظ كل matrices ويحسب الأربع queries
  من الـ engine ويصدّر scores وrankings؛ مش بيحط expected answers مكان الحساب.
- `load_model(root)`: يقرأ `model.json` ويتأكد من schema وfingerprint.
  لو outputs ناقصة أو قديمة يطلب `python run_spark.py` بدل بيانات قديمة.

### تشغيل المشروع والـ web

- `run_spark.main()`: يربط indexing بالحسابات والتصدير، ويحفظ processing metadata.
- `app.create_app(root)`: يحمّل model ويجهّز Flask routes. `page_view` للـ HTML،
  `model_data` للبيانات، `index_data` للـ postings، `search_data` للبحث،
  `export_status` لحالة الملفات، و`download` لملفات مسموحة أو ZIP حقيقي.
  `check_current_model` يتأكد إن الـ outputs لسه نفس النسخة المحمّلة،
  و`health` readiness check، و`stale_outputs` يرجّع رسالة واضحة لو الداتا اتغيرت.
- `launcher.acquire_instance_lock()`: OS lock يمنع اتنين launchers يشتغلوا مع بعض.
- `launcher.ready(url)`: يتأكد من HTTP response بتاع التطبيق، مش port مفتوح بس.
- `launcher.existing_instance(open_browser)`: يفتح النسخة الموجودة لو healthy.
- `launcher.main()`: يشغّل Waitress على loopback، يختار port فاضي لو محتاج،
  يفتح browser بعد الجاهزية، ويقفل server لما تضغط Enter. مفيش shutdown API.

### أهم JavaScript functions

- `request`: تبعت HTTP request وتعرض رسالة مفهومة لو backend رجّع error.
- `element`, `table`, `replace`, `link`, `button`: DOM helpers بسيطة؛ النصوص
  بتدخل بـ `textContent` عشان مفيش تفسير لكلام المستخدم كـ HTML.
- `highlight`: يلوّن tokens حسب ranges الحقيقية من backend.
- `dashboard`: يعرض KPIs والـ charts والـ pipeline من model.
- `indexExplorer`: يفلتر vocabulary ويعرض postings وdocument preview.
- `analytics`: يغيّر matrix والفلاتر والـ precision والـ heatmap من نفس البيانات.
- `queryPage`: يجمع المدخلات ويبعتها، ويحفظ آخر query في sessionStorage.
- `renderResults` و`resultCard`: يعرضوا ranking والـ phrase ranges والـ contributions.
- `renderMathematics`, `mathStep`, `queryTable`, `contributionTable`: يعرضوا
  العشر خطوات؛ تغيير document يغيّر المقارنة والـ dot product.
- `reports`: يتأكد من حالة الملفات ويعرض download links للملفات الموجودة فعلاً.
- `copy` و`toast`: نسخ ورسالة نجاح أو توضيح إن clipboard مش متاح.
- `barChart` في charts.js: يرسم values الحقيقية ويقفل chart القديمة قبل التحديث.

## Positional Index بمثال واضح

في d5 النص هو:

```text
machine learning machine models support data science and machine learning
1       2        3       4      5       6    7       8   9       10
```

إذن `machine → d5:[1,3,9]` و`learning → d5:[2,10]`.
عشان نطابق `machine learning`، نجرب starts من machine:

- عند 1، learning عند 2، إذن match في range 1–2.
- عند 3، learning مش عند 4، إذن مفيش match.
- عند 9، learning عند 10، إذن match تاني في 9–10.

مجرد إن الكلمتين موجودين في الملف مش كفاية؛ لازم ترتيب ومسافة بالظبط.

## الحسابات خطوة بخطوة

### Raw TF وWeighted TF

`TF(machine,d5)=3` عشان عندنا 3 positions. بالتالي:

```text
WeightedTF = 1 + log10(3) ≈ 1.4771
```

### DF وIDF

machine موجودة في d1 وd2 وd5 وd7 وd10، إذن DF = 5:

```text
IDF(machine) = log10(10/5) ≈ 0.3010
```

DF مش total occurrences. data منتشرة في 7 documents فـ IDF بتاعها أقل، حوالي
0.1549. science في 3 documents فـ IDF حوالي 0.5229.

### TF-IDF وDocument normalization

```text
TF-IDF(machine,d5) = 1.4771 × 0.3010 ≈ 0.4447
Length(d5) = sqrt(sum of squared TF-IDF weights) ≈ 1.5526
Normalized(machine,d5) ≈ 0.4447 / 1.5526 ≈ 0.2864
```

الأرقام المعروضة متقربة، لكن البرنامج بيحسب بالـ full precision.
الـ normalization بيخلينا نقارن اتجاه vectors بدل ما طول الملف لوحده يتحكم.

### Query vector وCosine Similarity

لما query تبقى `machine learning`، TF لكل كلمة = 1، والـ IDF لكل واحدة
0.3010 تقريبًا. طول query حوالي 0.425721، وبعد normalization كل وزن 0.7071.

```text
Similarity(q,d5) ≈ 0.7071×0.2864 + 0.7071×0.2523 ≈ 0.3809
```

إحنا بنعمل dot product لأن الاتنين normalized بالفعل. دوت مش جمع raw TF.
ترتيب النتيجة: **d1 > d5 > d10 > d2 > d7**. d1 نفس query بالظبط فدرجته 1.

## Boolean AND وAND NOT

```text
A = machine learning matches = {d1,d2,d5,d7,d10}
B = data science matches     = {d3,d5,d8}
AND     = A intersection B   = {d5}
AND NOT = A minus B          = {d1,d2,d7,d10}
```

في AND بنستخدم كلمات الاتنين في query vector، فـ d5 درجته 0.5113.
في AND NOT بنستخدم machine learning بس في scoring. data science شرط استبعاد
phrase كاملة. d2 وd10 فيهم data بس مش data science، فمش بنشيلهم.
ومش بنمسح weights من الـ original document vector.

## الواجهة بتساعدك تشرح إزاي؟

1. Overview: ورّي عدد الملفات والكلمات والـ pipeline والـ charts.
2. Positional Index: اختار machine ثم d5 واشرح `[1,3,9]`.
3. Analytics: ورّي الفرق بين Raw TF وWeighted TF وDF/IDF وباقي matrices.
4. Search: شغّل الأربع queries وورّي الفرق في sets وranking.
5. Query Mathematics: اختار d5 وامشي على الخطوات العشرة لحد dot product.
6. Export & Report: نزّل CSV/JSON أو ZIP حقيقي واعرض outputs المطلوبة.

## أشغّله إزاي؟

على Windows، افتح المشروع في VS Code. للـ GUI العادية double-click
`Launch_IR.bat`. أول مرة بيعمل venv ويثبّت Flask وWaitress، وبعدها النتائج
المحفوظة تشتغل من غير Spark. لو عندك executable مبني، افتح
`dist/IR_Search_Engine/IR_Search_Engine.exe` ومعاه باقي فولدره.

لو عايز تعيد preprocessing، شغّل Docker Desktop Linux containers، ومن
PowerShell في فولدر المشروع:

```powershell
docker build -t lumen-ir-spark .
docker run --rm -v "${PWD}:/project" lumen-ir-spark
.\.venv\Scripts\python.exe validate.py
```

لو full Python environment ومعاه Java 17/21 جاهز:

```text
python -m pip install -r requirements.txt
python run_spark.py
python validate.py
python launcher.py
```

ابنِ executable على Windows بـ `build_exe.bat`. البناء ده لسه مش متجرب
على Windows في بيئة التطوير Linux. اقفل التطبيق بـ Enter من console
الـ launcher. أو Ctrl+C لو مشغّله بـ `app.py`.

## خطة شرح قصيرة للمناقشة

ابدأ بالمشكلة والداتا، بعدين Spark index، بعدين formulas، بعدين query
واحدة كاملة، وبعدها Boolean difference. اختم بعرض ملفات outputs ونتيجة
`validate.py`. لو اتسألت عن رقم، افتح Mathematics بدل حفظه من غير فهم.

## أسئلة شفوي متوقعة

**ليه Spark مع إن الداتا صغيرة؟** لأنه مطلوب أكاديميًا، والـ pipeline فعلاً
Spark؛ الحجم الصغير يسمح نجمع index في driver بعد المعالجة.

**هل Flask بيشغّل Spark مع كل search؟** لا، preprocessing منفصل والنتائج
محفوظة؛ searching بيستخدم index وvectors المحسوبين.

**ليه weighted TF مش raw TF بس؟** الـ log يقلل التأثير الزائد للتكرار.

**إيه الفرق بين DF وTF؟** TF occurrences جوّه document؛ DF عدد documents
اللي فيها term مهما تكررت جوّه الواحد.

**ليه IDF يقل لما DF يزيد؟** عشان الكلمة الشائعة أقل قدرة على تمييز document.

**هل بنشيل and من الداتا؟** لا؛ مفيش stop-word removal حسب الـ specification.

**إيه يثبت phrase match؟** كل token عند start + offset؛ مش مجرد وجود الكلمات.

**لو query فيها كلمة مش موجودة؟** بنوضحها ومفيش exact phrase matches للكلمة دي.

**ليه d2 فضل في AND NOT؟** فيه data، لكن مفيش phrase كاملة data science.

**ممكن query يتكرر فيها term؟** آه، TF بيتحسب من query نفسها قبل weighting.

**ليه d1 درجته 1؟** vector اتجاهه نفس اتجاه machine learning query.

**هل بنقرّب أثناء الحساب؟** لا، rounding للعرض بس؛ الملفات كاملة الدقة.

**هل executable فيه Spark؟** لا؛ فيه GUI ونتائج Spark السابقة، وإعادة
المعالجة تفضل خطوة منفصلة وقابلة للتكرار.
