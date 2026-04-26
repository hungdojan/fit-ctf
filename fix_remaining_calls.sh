#!/bin/bash
# Script to help find remaining call sites that need updating

echo "=== Finding UserManager calls ==="
echo "disable_user calls:"
grep -rn "\.disable_user(" src/fit_ctf/ tests/ --include="*.py" | grep -v "def " | grep -v "enroll_mgr"

echo -e "\n=== Finding ProjectManager calls ==="
echo "disable_project calls:"
grep -rn "\.disable_project(" src/fit_ctf/ tests/ --include="*.py" | grep -v "def " | grep -v "enroll_mgr"
echo "flush_project calls:"
grep -rn "\.flush_project(" src/fit_ctf/ tests/ --include="*.py" | grep -v "def " | grep -v "enroll_mgr"

echo -e "\n=== Finding Progress method calls ==="
echo "submit_secret calls:"
grep -rn "\.submit_secret(" src/fit_ctf/ tests/ --include="*.py" | grep -v "def " | grep -v "prj_mgr, enroll_mgr"
echo "list_secrets_for_display calls:"
grep -rn "\.list_secrets_for_display(" src/fit_ctf/ tests/ --include="*.py" | grep -v "def " | grep -v "prj_mgr"
echo "count_submittable_slots calls:"
grep -rn "\.count_submittable_slots(" src/fit_ctf/ tests/ --include="*.py" | grep -v "def " | grep -v "prj_mgr"

echo -e "\n=== Finding UserClusterManager calls ==="
echo "start_cluster calls:"
grep -rn "\.start_cluster(" src/fit_ctf/ tests/ --include="*.py" | grep -v "def " | grep -v "enroll_mgr"
echo "stop_cluster calls:"
grep -rn "\.stop_cluster(" src/fit_ctf/ tests/ --include="*.py" | grep -v "def " | grep -v "enroll_mgr"

echo -e "\n=== Finding ModuleManager calls ==="
echo "reference_count calls:"
grep -rn "\.reference_count(" src/fit_ctf/ tests/ --include="*.py" | grep -v "def " | grep -v "prj_mgr, enroll_mgr"
echo "remove_module calls:"
grep -rn "\.remove_module(" src/fit_ctf/ tests/ --include="*.py" | grep -v "def " | grep -v "prj_mgr, enroll_mgr"
