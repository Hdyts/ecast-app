import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Test Arabic text
text = "\u0627\u0644\u0633\u0644\u0627\u0645 \u0639\u0644\u064a\u0643\u0645"
print(f"Original: [{text}]")
print(f"Repr: {repr(text)}")
print(f"Len: {len(text)}")

# Test regex step by step
step1 = re.sub('[\u0617-\u0652]', '', text)
print(f"After diacritics removal: [{step1}]")
print(f"Len after: {len(step1)}")

step2 = re.sub('[^\u0600-\u06FF ]', '', step1)
print(f"After keeping only Arabic+space: [{step2}]")
print(f"Len after: {len(step2)}")
