/* Separate-process checkpoint acceptance. Each phase execs a fresh Linux
 * program instance to prove file-backed persistence across process exit.
 * This is not a melonDS emulator gameplay test. */
#include "game.h"
#include "save_backend.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static void run_phase(const char *self,const char *phase,const char *root) {
    pid_t child=fork();
    assert(child>=0);
    if(child==0) {
        execl(self,self,phase,root,(char *)NULL);
        perror("exec");
        _exit(127);
    }
    int status=0;
    assert(waitpid(child,&status,0)==child);
    if(!WIFEXITED(status) || WEXITSTATUS(status)!=0) {
        fprintf(stderr,"FAIL: independent process for %s exited with status %d\n",
                phase,status);
        exit(1);
    }
}
static void load_game(SaveBackend *backend,Game *g) {
    game_new(g,987);
    assert(save_backend_load(backend,g));
}
static int find_species(Game *g) {
    for(unsigned seed=1;seed<=512;seed++) {
        game_new(g,seed);
        g->save.story_phase=1;
        g->save.cloud_count=2;
        g->save.orbs=1000;
        g->save.total_orbs=1000;
        game_begin_search(g,EXT_DOWSING);
        assert(g->screen==STATE_RADAR && g->active_clouds==2);
        g->clouds[0].alive=1;
        g->clouds[0].kind=1;
        g->clouds[0].x=70;g->clouds[0].y=90;
        g->clouds[1].alive=1;
        g->clouds[1].kind=0;
        g->clouds[1].x=180;g->clouds[1].y=90;
        g->aim_x=70;g->aim_y=90;
        game_fire(g);
        assert(g->screen==STATE_SPHERE);
        if(g->session_type==0 && g->session_species>=0 &&
           g->session_species<LEGEND_SPECIES_START)
            return g->session_species;
    }
    assert(!"No ordinary Pokémon encountered within deterministic search range");
    return -1;
}
static void assert_reward(const Game *g) {
    assert(g->save.pending_count==1);
    assert(g->save.pending[0]<LEGEND_SPECIES_START);
    assert(g->save.caught_count==1);
    assert(g->save.searches==1);
    assert(g->save.orbs==900);
    for(int i=0;i<MAX_ITEMS;i++) assert(g->save.pending_items[i]==0);
}
static void phase(const char *name,const char *root) {
    char rom[TW_MAX_PATH];
    assert(snprintf(rom,sizeof rom,"%s/DreamRadarDSi.nds",root)<(int)sizeof rom);
    SaveBackend backend;
    assert(save_backend_init(&backend,root,rom));
    Game g;
    if(strcmp(name,"start")==0) {
        int species=find_species(&g);
        assert(species>=0 && g.session_caught==-1);
        assert(g.save.pending_count==0 && g.save.caught_count==0);
        assert(g.radar_resume_pending && g.clouds[1].alive);
        assert(save_backend_write(&backend,&g));
    } else if(strcmp(name,"preflight")==0) {
        load_game(&backend,&g);
        assert(g.screen==STATE_SPHERE && g.session_type==0);
        assert(g.session_species>=0 && g.session_species<LEGEND_SPECIES_START);
        assert(g.save.pending_count==0 && g.save.caught_count==0);
        assert(g.save.searches==0 && g.save.orbs==900);
        assert(g.radar_resume_pending && g.clouds[1].alive);
    } else if(strcmp(name,"capture")==0) {
        load_game(&backend,&g);
        assert(g.screen==STATE_SPHERE);
        int species=g.session_species;
        assert(species>=0 && species<LEGEND_SPECIES_START);
        g.projectile_enabled=0;
        int moved=0;
        for(int tick=0;tick<240 && g.screen==STATE_SPHERE;tick++) {
            int x=g.sphere_x,y=g.sphere_y;
            game_tick(&g);
            if(g.screen!=STATE_SPHERE) break;
            if(g.sphere_x!=x || g.sphere_y!=y)moved=1;
            g.aim_x=g.sphere_x;
            g.aim_y=g.sphere_y;
            game_fire(&g);
        }
        assert(moved && g.screen==STATE_RESULTS);
        assert(g.session_caught==species && g.save.pending[0]==species);
        assert_reward(&g);
        assert(g.radar_resume_pending && g.clouds[1].alive);
        assert(save_backend_write(&backend,&g));
    } else if(strcmp(name,"result")==0) {
        load_game(&backend,&g);
        assert(g.screen==STATE_RESULTS && g.radar_resume_pending);
        assert_reward(&g);
        assert(g.session_caught==g.save.pending[0]);
    } else if(strcmp(name,"resume")==0) {
        load_game(&backend,&g);
        assert_reward(&g);
        assert(game_resume_radar(&g));
        assert(g.screen==STATE_RADAR && g.clouds[1].alive);
        assert_reward(&g);
        assert(save_backend_write(&backend,&g));
    } else if(strcmp(name,"radar")==0) {
        load_game(&backend,&g);
        assert(g.screen==STATE_RADAR && g.clouds[1].alive);
        assert_reward(&g);
    } else if(strcmp(name,"leave")==0) {
        load_game(&backend,&g);
        assert(g.screen==STATE_RADAR);
        assert(game_leave_search(&g));
        assert_reward(&g);
        assert(save_backend_write(&backend,&g));
    } else if(strcmp(name,"final")==0) {
        load_game(&backend,&g);
        assert(g.screen==STATE_RESULTS && !g.radar_resume_pending);
        assert_reward(&g);
    } else {
        fprintf(stderr,"Unknown process phase: %s\n",name);
        exit(2);
    }
}
int main(int argc,char **argv) {
    if(argc==3) {
        phase(argv[1],argv[2]);
        return 0;
    }
    if(argc!=1) return 2;
    char root[]="/tmp/dr_cross_process_restart_XXXXXX";
    assert(mkdtemp(root));
    const char *steps[]={"start","preflight","preflight","capture",
                         "result","result","resume","radar","leave","final","final"};
    for(size_t i=0;i<sizeof steps/sizeof steps[0];i++)
        run_phase(argv[0],steps[i],root);
    puts("PASS: Pokémon reward and radar search persisted across 11 separate Linux processes");
    return 0;
}
