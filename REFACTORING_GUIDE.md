# Refactoring Guide: Remaining Call Site Updates

## Summary

**Architecture complete!** EntityRepository created, all managers refactored, no circular dependencies.

**Remaining work**: Update ~40 call sites where methods now require manager parameters.

## Pattern to Follow

When a method signature changed from:
```python
async def disable_user(self, username: str):
```

To:
```python
async def disable_user(self, username: str, enroll_mgr: EnrollmentManager):
```

Update all calls from:
```python
await user_mgr.disable_user("user1")
```

To:
```python
await user_mgr.disable_user("user1", enroll_mgr)  # or ctf_base.enroll_mgr
```

---

## Method Signature Changes Reference

### UserManager
- `disable_user(username, enroll_mgr)` - was `disable_user(username)`
- `disable_multiple_users(usernames, enroll_mgr)` - was `disable_multiple_users(usernames)`
- `flush_multiple_users(usernames, enroll_mgr)` - was `flush_multiple_users(usernames)`

### ProjectManager
- `disable_project(project, enroll_mgr)` - was `disable_project(project)`
- `flush_project(project, enroll_mgr)` - was `flush_project(project)`
- `generate_port_forwarding_script(project, ip, file, enroll_mgr)` - was `...(project, ip, file)`

### EnrollmentManager (UserProgressManager methods)
- `submit_secret(enrollment, value, prj_mgr, enroll_mgr)` - was `submit_secret(enrollment, value)`
- `list_secrets_for_display(enrollment, prj_mgr, show_flag=False)` - was `list_secrets_for_display(enrollment, show_flag=False)`
- `count_submittable_slots(enrollment, prj_mgr)` - was `count_submittable_slots(enrollment)`
- `record_session(enrollment, state, enroll_mgr, info={})` - was `record_session(enrollment, state, info={})`

### UserClusterManager
- `start_cluster(cluster, enroll_mgr, *, verbose=False)` - was `start_cluster(cluster, *, verbose=False)`
- `stop_cluster(cluster, enroll_mgr, *, verbose=False)` - was `stop_cluster(cluster, *, verbose=False)`
- `stop_multiple_user_clusters(users, project, enroll_mgr)` - was `stop_multiple_user_clusters(users, project)`
- `stop_all_user_clusters(project, enroll_mgr)` - was `stop_all_user_clusters(project)`
- `stop_all_clusters_of_a_user(user, enroll_mgr)` - was `stop_all_clusters_of_a_user(user)`

### ModuleManager
- `reference_count(project_name, prj_mgr, enroll_mgr, all_images=False)` - was `reference_count(project_name, all_images=False)`
- `remove_module(module_name, prj_mgr, enroll_mgr)` - was `remove_module(module_name)`

---

## Remaining Call Sites to Fix

### 1. Internal Manager Calls (src/fit_ctf/models/)

**UserManager (src/fit_ctf/models/core/user.py):**
```python
# Line 470: delete_user method
await self.disable_user(username)
→ await self.disable_user(username, enroll_mgr)  # Add enroll_mgr parameter to delete_user method

# Lines 480-481: delete_multiple_users method
await self.disable_multiple_users(lof_usernames)
await self.flush_multiple_users(lof_usernames)
→ await self.disable_multiple_users(lof_usernames, enroll_mgr)
→ await self.flush_multiple_users(lof_usernames, enroll_mgr)  # Add enroll_mgr parameter to delete_multiple_users method
```

**ProjectManager (src/fit_ctf/models/core/project.py):**
```python
# Lines 376-377: delete_project method
await self.disable_project(prj)
await self.flush_project(prj)
→ await self.disable_project(prj, enroll_mgr)
→ await self.flush_project(prj, enroll_mgr)  # Add enroll_mgr parameter to delete_project method
```

**EnrollmentManager (src/fit_ctf/models/core/enrollment.py):**
```python
# Line 701: disable_enrollment method
await self._user_cluster_mgr.stop_cluster(cluster)
→ await self._user_cluster_mgr.stop_cluster(cluster, self)

# Line 735: disable_multiple_enrollments method
await self._user_cluster_mgr.stop_cluster(cluster)
→ await self._user_cluster_mgr.stop_cluster(cluster, self)
```

**UserClusterManager (src/fit_ctf/models/infra/user_cluster.py):**
```python
# Line 388: restart_cluster method
await self.stop_cluster(cluster)
→ await self.stop_cluster(cluster, enroll_mgr)  # Add enroll_mgr parameter to restart_cluster method

# Lines 528-529: restart_cluster method
await self.stop_cluster(cluster, verbose=verbose)
await self.start_cluster(cluster, verbose=verbose)
→ await self.stop_cluster(cluster, enroll_mgr, verbose=verbose)
→ await self.start_cluster(cluster, enroll_mgr, verbose=verbose)  # Add enroll_mgr parameter to restart_cluster
```

### 2. CLI Commands (src/fit_ctf_cli/commands/)

**Need to find and update calls in CLI commands. Pattern:**
```python
# In CLI command functions
ctf_app = ctx.obj["ctf_app"]  # or similar
prj_mgr = ctf_app.prj_mgr
enroll_mgr = ctf_app.enroll_mgr

# Then pass enroll_mgr where needed:
await prj_mgr.disable_project(project_name, enroll_mgr)
```

Search files:
- `src/fit_ctf_cli/commands/user.py`
- `src/fit_ctf_cli/commands/project.py`
- `src/fit_ctf_cli/commands/cluster.py`
- `src/fit_ctf_cli/commands/user_progress.py`

### 3. Test Files

**Backend tests (tests/backend/):**
```bash
# Find all calls
grep -rn "\.disable_user\|\.disable_project\|\.submit_secret" tests/backend/ --include="*.py" | grep -v "def "

# Pattern: Add ctf_app.enroll_mgr or ctf_app.prj_mgr as needed
```

**CLI tests (tests/cli/):**
```bash
# Find CLI test calls
grep -rn "disable\|flush\|submit\|start_cluster\|stop_cluster" tests/cli/ --include="*.py" | grep -v "def "
```

---

## Quick Fix Script

Save this as `fix_call_sites.sh` and run it:

```bash
#!/bin/bash

# Fix internal manager calls (self-calls)
echo "Fixing internal manager calls..."

# UserManager.delete_user
sed -i '' 's/await self\.disable_user(username)/await self.disable_user(username, enroll_mgr)/g' src/fit_ctf/models/core/user.py
sed -i '' 's/await self\.disable_multiple_users(lof_usernames)/await self.disable_multiple_users(lof_usernames, enroll_mgr)/g' src/fit_ctf/models/core/user.py
sed -i '' 's/await self\.flush_multiple_users(lof_usernames)/await self.flush_multiple_users(lof_usernames, enroll_mgr)/g' src/fit_ctf/models/core/user.py

# ProjectManager.delete_project
sed -i '' 's/await self\.disable_project(prj)/await self.disable_project(prj, enroll_mgr)/g' src/fit_ctf/models/core/project.py
sed -i '' 's/await self\.flush_project(prj)/await self.flush_project(prj, enroll_mgr)/g' src/fit_ctf/models/core/project.py

# EnrollmentManager calls
sed -i '' 's/await self\._user_cluster_mgr\.stop_cluster(cluster)/await self._user_cluster_mgr.stop_cluster(cluster, self)/g' src/fit_ctf/models/core/enrollment.py

echo "Done! Review changes and add 'enroll_mgr' parameters to method signatures."
```

---

## Remaining Tasks Checklist

### Internal Methods (need enroll_mgr parameter added)

- [ ] `UserManager.delete_user` - add `enroll_mgr` parameter
- [ ] `UserManager.delete_multiple_users` - add `enroll_mgr` parameter
- [ ] `ProjectManager.delete_project` - add `enroll_mgr` parameter
- [ ] `UserClusterManager.restart_cluster` - add `enroll_mgr` parameter

### EnrollmentManager Internal Calls

- [ ] Line 701: `self._user_cluster_mgr.stop_cluster(cluster)` → `stop_cluster(cluster, self)`
- [ ] Line 735: `self._user_cluster_mgr.stop_cluster(cluster)` → `stop_cluster(cluster, self)`

### UserClusterManager Internal Calls

- [ ] Line 388: `self.stop_cluster(cluster)` → `stop_cluster(cluster, enroll_mgr)`
- [ ] Lines 528-529: `stop/start_cluster` → add `enroll_mgr`
- [ ] Line 604: `self.stop_cluster(cluster, enroll_mgr)` - already done

### CLI Commands (src/fit_ctf_cli/commands/)

Search pattern:
```bash
# Find all CLI calls to updated methods
grep -rn "disable_user\|disable_project\|flush_project\|submit_secret\|start_cluster\|stop_cluster\|reference_count\|remove_module" src/fit_ctf_cli/ --include="*.py" | grep -v "def "
```

For each:
1. Get `ctf_app` from context
2. Get `enroll_mgr = ctf_app.enroll_mgr` or `prj_mgr = ctf_app.prj_mgr`
3. Pass as additional parameter

### Test Files (tests/)

```bash
# Find remaining test calls
grep -rn "submit_secret\|list_secrets\|count_submittable\|record_session" tests/ --include="*.py" | grep -v "def "

# For each call, add: ctf_app.prj_mgr, ctf_app.enroll_mgr as needed
```

---

## Verification

After updates:
```bash
# Run tests
poetry run pytest tests/ -v

# Should see: 112 passed!

# Test CLI
poetry run fit-ctf project ls
poetry run fit-ctf user ls
```

---

## Common Patterns

**In managers (self-calls):**
```python
# Before
await self.disable_user(username)

# After - add enroll_mgr to method signature first!
async def delete_user(self, username: str, enroll_mgr: EnrollmentManager):
    await self.disable_user(username, enroll_mgr)
```

**In CLI:**
```python
# Before
await prj_mgr.disable_project(project_name)

# After
enroll_mgr = ctf_app.enroll_mgr
await prj_mgr.disable_project(project_name, enroll_mgr)
```

**In tests:**
```python
# Before
ctf_app.enroll_mgr.submit_secret(enrollment, "value")

# After
ctf_app.enroll_mgr.submit_secret(enrollment, "value", ctf_app.prj_mgr, ctf_app.enroll_mgr)
```

---

## Files Requiring Updates (Priority Order)

1. ✅ `src/fit_ctf/models/core/repository.py` - DONE
2. ✅ `src/fit_ctf/models/core/enrollment.py` - Constructor done, need 2 call site fixes
3. ✅ `src/fit_ctf/models/core/user.py` - Constructor done, need 3 call site fixes
4. ✅ `src/fit_ctf/models/core/project.py` - Constructor done, need 2 call site fixes
5. ✅ `src/fit_ctf/models/infra/user_cluster.py` - Methods done, need 3 call site fixes
6. ✅ `tests/backend/test_progress.py` - DONE
7. ⏳ `tests/backend/test_user.py` - Partial
8. ⏳ `tests/backend/test_project.py` - Partial
9. ⏳ `tests/backend/test_enroll.py` - Partial
10. ⏳ `src/fit_ctf_cli/commands/` - All CLI commands
11. ⏳ `tests/cli/` - All CLI tests
12. ⏳ `tests/workflow/` - Workflow tests

---

## Quick Reference

**Where to get managers in different contexts:**

```python
# In managers (self-calls)
# Must add parameter to method signature!
async def method_a(self, enroll_mgr: EnrollmentManager):
    await self.method_b(x, enroll_mgr)

# In CLI commands
ctf_app = ctx.obj["ctf_app"]
enroll_mgr = ctf_app.enroll_mgr
prj_mgr = ctf_app.prj_mgr

# In tests
ctf_app.enroll_mgr
ctf_app.prj_mgr
ctf_app.user_mgr
```

**Current test status:** 63 passed, 49 failed (all parameter mismatches - easy to fix!)
