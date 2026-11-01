#include "platform_compat.h"
#include <assert.h>
#include <stdio.h>
int main(void){
    int armed=0;
    /* The A press from an Extensions selection must not shoot anything.
       Holding across multiple VBlanks must not bypass the guard. */
    for(int i=0;i<100;i++)assert(dr_search_fire_gate(1,&armed)==0);
    assert(armed==0);
    /* A full release is required before the first shot. */
    assert(dr_search_fire_gate(0,&armed)==0);
    assert(armed==1);
    for(int i=0;i<10;i++)assert(dr_search_fire_gate(1,&armed)==1);
    /* Resume from results or start a new search: re-arm independently. */
    armed=0;
    assert(dr_search_fire_gate(1,&armed)==0);
    assert(dr_search_fire_gate(0,&armed)==0);
    assert(dr_search_fire_gate(1,&armed)==1);
    assert(dr_search_fire_gate(1,NULL)==0);
    assert(dr_search_fire_gate(0,NULL)==0);
    puts("PASS: Search A press cannot fire a cloud until A has been released");
    return 0;
}
