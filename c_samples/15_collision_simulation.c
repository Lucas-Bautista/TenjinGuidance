#include <stdio.h>

/*
 * 2D physics-lite simulation:
 *   - Point-in-circle / point-in-rectangle tests
 *   - Circle-circle collision detection
 *   - AABB overlap detection
 *   - Simple Euler-method trajectory simulation with gravity
 *   - Tracks collisions over multiple timesteps
 */

#define MAX_BODIES 20
#define MAX_STEPS 500

int main(void) {
    /* Body data stored in parallel arrays (primitives only) */
    double pos_x[MAX_BODIES];
    double pos_y[MAX_BODIES];
    double vel_x[MAX_BODIES];
    double vel_y[MAX_BODIES];
    double radius[MAX_BODIES];
    double mass[MAX_BODIES];
    int active[MAX_BODIES];
    int num_bodies = 8;

    /* Initialize bodies in a pattern */
    unsigned int seed = 7777u;
    int i;
    for (i = 0; i < num_bodies; i++) {
        seed = seed * 1664525u + 1013904223u;
        pos_x[i] = (double)((seed >> 16) % 800) / 10.0;

        seed = seed * 1664525u + 1013904223u;
        pos_y[i] = (double)((seed >> 16) % 600) / 10.0 + 20.0;

        seed = seed * 1664525u + 1013904223u;
        vel_x[i] = ((double)((seed >> 16) % 200) - 100.0) / 50.0;

        seed = seed * 1664525u + 1013904223u;
        vel_y[i] = ((double)((seed >> 16) % 100)) / 50.0;

        radius[i] = 1.0 + (double)(i % 3) * 0.5;
        mass[i] = radius[i] * radius[i] * 3.14159;
        active[i] = 1;
    }

    /* Simulation parameters */
    double dt = 0.05;
    double gravity = -9.81;
    double floor_y = 0.0;
    double ceiling_y = 100.0;
    double wall_left = 0.0;
    double wall_right = 80.0;
    double restitution = 0.85;  /* bounce coefficient */

    int total_collisions = 0;
    int wall_bounces = 0;
    int floor_bounces = 0;
    int body_collisions = 0;

    /* Simulation loop */
    int step;
    for (step = 0; step < MAX_STEPS; step++) {

        /* Apply gravity and update positions (Euler method) */
        for (i = 0; i < num_bodies; i++) {
            if (!active[i]) continue;

            vel_y[i] += gravity * dt;
            pos_x[i] += vel_x[i] * dt;
            pos_y[i] += vel_y[i] * dt;
        }

        /* Wall and floor collisions */
        for (i = 0; i < num_bodies; i++) {
            if (!active[i]) continue;

            /* Floor */
            if (pos_y[i] - radius[i] < floor_y) {
                pos_y[i] = floor_y + radius[i];
                vel_y[i] = -vel_y[i] * restitution;
                floor_bounces++;
                total_collisions++;
            }

            /* Ceiling */
            if (pos_y[i] + radius[i] > ceiling_y) {
                pos_y[i] = ceiling_y - radius[i];
                vel_y[i] = -vel_y[i] * restitution;
                total_collisions++;
            }

            /* Left wall */
            if (pos_x[i] - radius[i] < wall_left) {
                pos_x[i] = wall_left + radius[i];
                vel_x[i] = -vel_x[i] * restitution;
                wall_bounces++;
                total_collisions++;
            }

            /* Right wall */
            if (pos_x[i] + radius[i] > wall_right) {
                pos_x[i] = wall_right - radius[i];
                vel_x[i] = -vel_x[i] * restitution;
                wall_bounces++;
                total_collisions++;
            }
        }

        /* Circle-circle collision detection */
        int a, b;
        for (a = 0; a < num_bodies; a++) {
            if (!active[a]) continue;
            for (b = a + 1; b < num_bodies; b++) {
                if (!active[b]) continue;

                double dx = pos_x[b] - pos_x[a];
                double dy = pos_y[b] - pos_y[a];
                double dist_sq = dx * dx + dy * dy;
                double min_dist = radius[a] + radius[b];
                double min_dist_sq = min_dist * min_dist;

                if (dist_sq < min_dist_sq && dist_sq > 0.0001) {
                    body_collisions++;
                    total_collisions++;

                    /* Approximate sqrt via Newton's method (3 iterations) */
                    double dist = dist_sq / 2.0;
                    int iter;
                    for (iter = 0; iter < 10; iter++) {
                        dist = (dist + dist_sq / dist) / 2.0;
                    }

                    /* Normalize collision vector */
                    double nx = dx / dist;
                    double ny = dy / dist;

                    /* Relative velocity along collision normal */
                    double dvx = vel_x[a] - vel_x[b];
                    double dvy = vel_y[a] - vel_y[b];
                    double rel_vel = dvx * nx + dvy * ny;

                    /* Only resolve if objects are approaching */
                    if (rel_vel > 0.0) {
                        double total_mass = mass[a] + mass[b];
                        double impulse = (1.0 + restitution) * rel_vel / total_mass;

                        vel_x[a] -= impulse * mass[b] * nx;
                        vel_y[a] -= impulse * mass[b] * ny;
                        vel_x[b] += impulse * mass[a] * nx;
                        vel_y[b] += impulse * mass[a] * ny;

                        /* Separate overlapping bodies */
                        double overlap = min_dist - dist;
                        double sep = overlap / 2.0 + 0.01;
                        pos_x[a] -= sep * nx;
                        pos_y[a] -= sep * ny;
                        pos_x[b] += sep * nx;
                        pos_y[b] += sep * ny;
                    }
                }
            }
        }
    }

    /* Compute final kinetic energy */
    double total_ke = 0.0;
    double max_speed = 0.0;
    double min_height = ceiling_y;
    double max_height = floor_y;

    for (i = 0; i < num_bodies; i++) {
        if (!active[i]) continue;
        double speed_sq = vel_x[i] * vel_x[i] + vel_y[i] * vel_y[i];
        double ke = 0.5 * mass[i] * speed_sq;
        total_ke += ke;

        /* sqrt of speed_sq */
        double speed = speed_sq / 2.0;
        int iter;
        for (iter = 0; iter < 10 && speed > 0.0; iter++) {
            speed = (speed + speed_sq / speed) / 2.0;
        }
        if (speed > max_speed) max_speed = speed;
        if (pos_y[i] < min_height) min_height = pos_y[i];
        if (pos_y[i] > max_height) max_height = pos_y[i];
    }

    /* Report */
    printf("=== 2D Physics Simulation ===\n");
    printf("Bodies: %d, Steps: %d, dt=%.3f\n\n", num_bodies, MAX_STEPS, dt);

    printf("Final positions:\n");
    for (i = 0; i < num_bodies; i++) {
        printf("  Body %d: pos=(%.2f, %.2f) vel=(%.2f, %.2f) r=%.1f m=%.2f\n",
               i, pos_x[i], pos_y[i], vel_x[i], vel_y[i], radius[i], mass[i]);
    }

    printf("\nCollision summary:\n");
    printf("  Total:  %d\n", total_collisions);
    printf("  Floor:  %d\n", floor_bounces);
    printf("  Wall:   %d\n", wall_bounces);
    printf("  Bodies: %d\n", body_collisions);

    printf("\nFinal state:\n");
    printf("  Total KE:    %.4f\n", total_ke);
    printf("  Max speed:   %.4f\n", max_speed);
    printf("  Height range: [%.2f, %.2f]\n", min_height, max_height);

    return 0;
}
