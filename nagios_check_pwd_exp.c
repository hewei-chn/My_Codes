/**************************************************************************
 * Nagios Plugin to Check User Password Expiration stat.
 * Created by weihe#corp.netease.com 20130228
 * Version v0.1
 * Usage: ./a.out                                  to check all users.
 *        ./a.out user_a user_b user_and_so_on     to check a list of users.
 * Return:
 *        "User_expire:OK" With retcode 0 OR
 *        "User_expire:CRITICAL"
 *        "userA:daysToExpire"
 *        "userB:-daysHasExpire" ... With retcode 2
 ***************************************************************************/

#include <unistd.h>
#include <stdio.h>
#include <shadow.h>
#include <time.h>

struct spwd * get_user_spwd(int argc, char ** argv)
{
	static cur_index = 1;
	struct spwd * ptr = NULL;
	if (argc == 1) {
		return getspent();
	} else {
		while(cur_index < argc && !(ptr = getspnam(argv[cur_index++]))){/*Nothing but continue;*/};
		return ptr;
	}
}


int main(int argc, char ** argv)
{
	struct spwd * user = NULL;
	time_t secs = time(NULL);
	long int today = secs/(24*60*60);
	int head_flag = 0;
	
//printf("Today is %d\n", today);
	
	while (user = get_user_spwd(argc, argv)) {
/*		printf("Username:%s,Password:%s,sp_lstchg:%d,sp_min:%d,sp_max:%d,sp_warn:%d,sp_inact,%d,sp_expire:%d,sp_flag:%d\n",
				user->sp_namp,
				user->sp_pwdp,
				user->sp_lstchg,
				user->sp_min,
				user->sp_max,
				user->sp_warn,
				user->sp_inact,
				user->sp_expire,
				user->sp_flag);
*/
		if (user->sp_expire > 0 && user->sp_expire - today <= user->sp_warn) {
			if (!head_flag) {
				printf("User_expire: CRITICAL\n");
				head_flag = 1;
			}
			printf("%s:%d\n",user->sp_namp, user->sp_expire - today);
		}
	}

	if (head_flag)
		return 2;
	else
		printf("User_expire: OK\n");

	return 0;
}
