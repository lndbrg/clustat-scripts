This script acts as a safe guard against running
cron jobs on non functional clusters (e.g state is not 'started').
If you do not pass any group names the script parses the cluster
group names from the output of clustat.
