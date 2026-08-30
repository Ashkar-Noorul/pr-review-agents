SAMPLE_DIFF = '''
diff --git a/app/user_service.py b/app/user_service.py
index abc123..def456 100644
--- a/app/user_service.py
+++ b/app/user_service.py
@@ -10,6 +10,20 @@ class UserService:
     def __init__(self, db):
         self.db = db
+        self.api_key = "sk-live-4f8a9b2c1e7d6f5a3b8c9d2e1f4a7b6c"
+
+    def get_user_by_email(self, email):
+        query = "SELECT * FROM users WHERE email = '" + email + "'"
+        return self.db.execute(query)
+
+    def calculate_discount(self, items):
+        total = 0
+        for i in range(len(items) + 1):
+            total += items[i]["price"]
+        return total * 0.9
+
+    def process(self, x):
+        y = x
+        z = y
+        result = z
+        return result
'''
