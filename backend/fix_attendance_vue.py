"""Fix TypeScript patterns in Vue files after script re-creation"""
import pathlib

def fix_file(path, replacements):
    content = pathlib.Path(path).read_text()
    changed = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            changed = True
    if changed:
        pathlib.Path(path).write_text(content)
        print(f"  Fixed {path.name}")
    else:
        print(f"  {path.name} - no changes needed")

# Fix AttendanceRuleList.vue
fix_file("/opt/adcraft/frontend/src/views/attendance/AttendanceRuleList.vue", [
    ("rules.value = res.data || []", "rules.value = res || []"),
])

# Fix AttendanceRecordList.vue
fix_file("/opt/adcraft/frontend/src/views/attendance/AttendanceRecordList.vue", [
    ("res.data?.items", "res?.items"),
    ("res.data?.total", "res?.total"),
    ("employees.value = res.data || []", "employees.value = res || []"),
])

print("Done fixing TS issues")
