check: ;
	pre-commit run --all-files

commit: ;
	git add -A
	git commit
	git pull
	git push
