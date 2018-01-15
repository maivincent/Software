#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Path planning for duckietown parking_space
Samuel Nyffenegger
"""

import dubins_path_planning as dpp
import rrt_star_car as rrt_star
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from math import sin, cos, sqrt, atan2, degrees, radians, pi
from numpy import sign
import os, pickle, sys

"""
Global parameters
"""
# control parameters
choose_random_parking_space_combination = False
close_itself = False
save_figures = True
pause_per_path = 0.5 # sec
ploting = True

# path planning parameters
radius_robot = 60                   # mm distance point between wheels and most apart point on robot
straight_in_parking_space = True    # robot drives last forward bit straigt (robustness increase)
straight_at_entrance = True         # robot drives last forward bit straigt (robustness increase)
primitive_backwards = True          # drive backwards and plan afterwards
allow_backwards_on_circle = False   # use this later together with reeds sheep
curvature = 60 #120                     # mm minimal turning radius
n_nodes_primitive = 50              # -
distance_backwards = 400            # mm
maxIter = 100                        # iterations for RRT*
rrt_star_animation = True           # animate RRT* search
radius_graph_refinement = 400       # mm radius arround new point for rewire

# parking lot parameters
lot_width = 2*585                   # mm, lot = 2x2 squares
lot_height = 2*585                  # mm
wide_tape_width = 50                # mm, red, white
narrow_tape_width = 25              # mm, yellow
april_tag_basement_length = 50      # mm,
april_tag_screen_length = 80        # mm
space_length = 270                  # mm from border, without april tag
lanes_length = 310                  # mm at entrance, exit

# additional constants
length_red_line = (lot_width/2.0 - 2.0*wide_tape_width - 1.0*narrow_tape_width) / 2.0

# plotting parameters
visual_boundairy = 100              # mm
add_april_tags = True               # enable dark green rectangles for april tags

"""
Functions
"""
# init once
def init():
    # delete saved images if there are any
    if save_figures and len([name for name in os.listdir('images/') if os.path.isfile(name)]) > 1:
        os.system("rm images/*")

# init for every new path
def initialize(start_number_manual=None, end_number_manual=None):
    if choose_random_parking_space_combination:
        entrance_exit = np.random.random_integers(0, 1)*7;
        parking_space = np.random.random_integers(1, 6);
        if entrance_exit == 0:
            start_number = entrance_exit
            end_number = parking_space
        else:
            start_number = parking_space
            end_number = entrance_exit
    else:
        start_number = start_number_manual
        end_number = end_number_manual

    start_x, start_y, start_yaw = pose_from_key(start_number)
    end_x, end_y, end_yaw = pose_from_key(end_number)

    return start_x, start_y, start_yaw, start_number, end_x, end_y, end_yaw, end_number

# pose assigenment: entrance, parking space, exit
def pose_from_key(key):
    if key == "entrance" or key == 0:
        return np.array([wide_tape_width+length_red_line/2.0,
        lot_height-lanes_length/4.0*2.0, -pi/2.0])
    elif key == "space 1" or key == 1:
        return np.array([lot_width/8.0, space_length/2.0, -pi/2.0])
    elif key == "space 2" or key == 2:
        return np.array([lot_width/8.0 + lot_width/4.0,
        space_length/2.0, -pi/2.0])
    elif key == "space 3" or key == 3:
        return np.array([lot_width/8.0 + 2*lot_width/4.0,
        space_length/2.0, -pi/2.0])
    elif key == "space 4" or key == 4:
        return np.array([lot_width/8.0 + 3*lot_width/4.0,
        space_length/2.0, -pi/2.0])
    elif key == "space 5" or key == 5:
        return np.array([lot_width/8.0 + 2*lot_width/4.0,
        lot_height-space_length/2.0, pi/2.0])
    elif key == "space 6" or key == 6:
        return np.array([lot_width/8.0 + 3*lot_width/4.0,
        lot_height-space_length/2.0, pi/2.0])
    elif key == "exit" or key == 7:
        return np.array([wide_tape_width+narrow_tape_width+3.0/2.0*length_red_line,
        lot_height-lanes_length/4.0*2.0, pi/2.0])
    elif key == "watch" or key == 8:
        return np.array([lot_width/2.0, lot_height/2.0, 0.0])
    else:
        print("parking space '{}' not found".format(key))
        exit(1)

# define objects and obstacles
def define_objects():
    # (x, y, dx, dy, colour, driveable)
    objects = []
    objects.append((0.0,0.0, narrow_tape_width, space_length, "b", True))
    objects.append((lot_width/4.0-narrow_tape_width/2.0,0.0, narrow_tape_width, space_length, "b", True))
    objects.append((lot_width/2.0-narrow_tape_width/2.0,0.0, narrow_tape_width, space_length, "b", True))
    objects.append((lot_width/4.0*3.0-narrow_tape_width/2.0,0.0, narrow_tape_width, space_length, "b", True))
    objects.append((lot_width-narrow_tape_width,0.0, narrow_tape_width, space_length, "b", True))
    objects.append((lot_width/4.0*3.0-narrow_tape_width/2.0, lot_height-space_length, narrow_tape_width, space_length, "b", True))
    objects.append((wide_tape_width+length_red_line, lot_height-lanes_length, narrow_tape_width, lanes_length, "y", True))
    objects.append((0.0,lot_height-lanes_length, wide_tape_width,lanes_length, "w", True))
    objects.append((lot_width/2.0-wide_tape_width,lot_height-lanes_length, wide_tape_width,lanes_length, "w", False)) # False
    objects.append((wide_tape_width,lot_height-lanes_length,length_red_line, wide_tape_width, "r", True))
    objects.append((wide_tape_width+narrow_tape_width+length_red_line, lot_height-wide_tape_width,length_red_line, wide_tape_width, "r", True))
    # objects.append((wide_tape_width+narrow_tape_width+length_red_line, lot_height-lanes_length,length_red_line, wide_tape_width, "m", False))

    # define object in the middle of parking lot to simulate path planning with RRT*
    size = 100;
    objects.append((lot_width/2.0-size/2.0,lot_height/2.0-size/2.0,size,size,'k',False))

    # parked duckiebot at space 5
    x, y ,yaw = pose_from_key(5)
    objects.append((x-radius_robot*0.75,y-radius_robot,radius_robot*2*0.75,2.0*radius_robot,'k',False))

    # april tags
    size = [80,50] # dx, dy
    dark_green = (0.0, 0.2, 0.0)
    if add_april_tags:
        # for i in range(6):
        #     x, y, yaw = pose_from_key(i+1)
        #     if i+1 < 5: # lower parking space
        #         objects.append((x-size[0]/2.0,0.0,size[0],size[1],dark_green, True))
        #     else: # upper parking space
        #         objects.append((x-size[0]/2.0,lot_height-size[1],size[0],size[1],dark_green, True))
        x, y = 0,0
        dx, dy = 100, 0
        for i in range(4):
            objects.append((x+(i+1)*dx,y+(i+1)*dy,size[0],size[1],dark_green,True))



    return objects

def define_obstacles(objects):
    # rectangle, x, y, dx, dy
    # circle, x, y, r
    obstacles = []
    for obj in objects:
        if not obj[5]: # object not driveable
            # current implementation only valid if object is a rectangle
            obstacles.append( ("rectangle", obj[0]-radius_robot, obj[1], obj[2]+2.0*radius_robot, obj[3] ))
            obstacles.append( ("rectangle", obj[0], obj[1]-radius_robot, obj[2], obj[3]+2.0*radius_robot ))
            obstacles.append( ("circle", obj[0], obj[1], radius_robot ))
            obstacles.append( ("circle", obj[0]+obj[2], obj[1], radius_robot ))
            obstacles.append( ("circle", obj[0], obj[1]+obj[3], radius_robot ))
            obstacles.append( ("circle", obj[0]+obj[2], obj[1]+obj[3], radius_robot ))

    return obstacles

# dubins path planning
def dubins_path_planning(start_x, start_y, start_yaw, end_x, end_y, end_yaw):
    # heuristics using path primitives
    detect_space_14 = (start_y < space_length and  (abs(start_yaw+radians(90))<radians(45)))
    detect_space_56 = lot_height- start_y < space_length and  abs(start_yaw-radians(90))<radians(45) and lot_width/2.0 < start_x
    if primitive_backwards and (detect_space_14 or detect_space_56):
        dt = distance_backwards/n_nodes_primitive
        px_backwards = [start_x]
        py_backwards = [start_y]
        pyaw_backwards = [start_yaw]
        for i in range(n_nodes_primitive):
            px_backwards.append(px_backwards[-1] - dt * cos(pyaw_backwards[-1]))
            py_backwards.append(py_backwards[-1] - dt * sin(pyaw_backwards[-1]))
            pyaw_backwards.append(pyaw_backwards[-1])
        start_x = px_backwards[-1]
        start_y = py_backwards[-1]
        start_yaw = pyaw_backwards[-1]

    start_x_0, start_y_0, start_yaw_0 = pose_from_key(0)
    straight_at_entrance_ = (straight_at_entrance and abs(start_x-start_x_0)<1.0 and abs(start_y-start_y_0)<1.0 and abs(start_yaw-start_yaw_0)<1.0)
    if straight_at_entrance_:
        dt = space_length/2.0/n_nodes_primitive
        px_straight_entrance = [start_x]
        py_straight_entrance = [start_y]
        pyaw_straight_entrance = [start_yaw]
        for i in range(n_nodes_primitive):
            px_straight_entrance.append(px_straight_entrance[-1] + dt * cos(pyaw_straight_entrance[-1]))
            py_straight_entrance.append(py_straight_entrance[-1] + dt * sin(pyaw_straight_entrance[-1]))
            pyaw_straight_entrance.append(pyaw_straight_entrance[-1])
        start_x = px_straight_entrance[-1]
        start_y = py_straight_entrance[-1]
        start_yaw = pyaw_straight_entrance[-1]

    if straight_in_parking_space:
        dt = space_length/2.0/n_nodes_primitive
        px_straight = [end_x]
        py_straight = [end_y]
        pyaw_straight = [end_yaw]
        for i in range(n_nodes_primitive):
            px_straight.append(px_straight[-1] - dt * cos(pyaw_straight[-1]))
            py_straight.append(py_straight[-1] - dt * sin(pyaw_straight[-1]))
            pyaw_straight.append(pyaw_straight[-1])
        end_x = px_straight[-1]
        end_y = py_straight[-1]
        end_yaw = pyaw_straight[-1]
        px_straight.reverse()
        py_straight.reverse()
        pyaw_straight.reverse()

    # actual path plannign using dubin curves
    px, py, pyaw, mode, clen = dpp.dubins_path_planning(start_x,
    start_y, start_yaw, end_x, end_y, end_yaw, curvature,
    allow_backwards_on_circle)

    # add path primitives to path
    if primitive_backwards and (detect_space_14 or detect_space_56):
        px = px_backwards + px
        py = py_backwards + py
        pyaw = pyaw_backwards + pyaw

    if straight_at_entrance_:
        px = px_straight_entrance + px
        py = py_straight_entrance + py
        pyaw = pyaw_straight_entrance + pyaw

    if straight_in_parking_space:
        px = px + px_straight
        py = py + py_straight
        pyaw = pyaw + pyaw_straight

    return px, py, pyaw

# RRT_star_path_planning
def RRT_star_path_planning(start_x, start_y, start_yaw, end_x, end_y, end_yaw, obstacles):
    # heuristics using path primitives
    detect_space_14 = (start_y < space_length and  (abs(start_yaw+radians(90))<radians(45)))
    detect_space_56 = lot_height- start_y < space_length and  abs(start_yaw-radians(90))<radians(45) and lot_width/2.0 < start_x
    if primitive_backwards and (detect_space_14 or detect_space_56):
        dt = distance_backwards/n_nodes_primitive
        px_backwards = [start_x]
        py_backwards = [start_y]
        pyaw_backwards = [start_yaw]
        for i in range(n_nodes_primitive):
            px_backwards.append(px_backwards[-1] - dt * cos(pyaw_backwards[-1]))
            py_backwards.append(py_backwards[-1] - dt * sin(pyaw_backwards[-1]))
            pyaw_backwards.append(pyaw_backwards[-1])
        start_x = px_backwards[-1]
        start_y = py_backwards[-1]
        start_yaw = pyaw_backwards[-1]

    start_x_0, start_y_0, start_yaw_0 = pose_from_key(0)
    straight_at_entrance_ = (straight_at_entrance and abs(start_x-start_x_0)<1.0 and abs(start_y-start_y_0)<1.0 and abs(start_yaw-start_yaw_0)<1.0)
    if straight_at_entrance_:
        dt = space_length/2.0/n_nodes_primitive
        px_straight_entrance = [start_x]
        py_straight_entrance = [start_y]
        pyaw_straight_entrance = [start_yaw]
        for i in range(n_nodes_primitive):
            px_straight_entrance.append(px_straight_entrance[-1] + dt * cos(pyaw_straight_entrance[-1]))
            py_straight_entrance.append(py_straight_entrance[-1] + dt * sin(pyaw_straight_entrance[-1]))
            pyaw_straight_entrance.append(pyaw_straight_entrance[-1])
        start_x = px_straight_entrance[-1]
        start_y = py_straight_entrance[-1]
        start_yaw = pyaw_straight_entrance[-1]

    if straight_in_parking_space:
        dt = space_length/2.0/n_nodes_primitive
        px_straight = [end_x]
        py_straight = [end_y]
        pyaw_straight = [end_yaw]
        for i in range(n_nodes_primitive):
            px_straight.append(px_straight[-1] - dt * cos(pyaw_straight[-1]))
            py_straight.append(py_straight[-1] - dt * sin(pyaw_straight[-1]))
            pyaw_straight.append(pyaw_straight[-1])
        end_x = px_straight[-1]
        end_y = py_straight[-1]
        end_yaw = pyaw_straight[-1]
        px_straight.reverse()
        py_straight.reverse()
        pyaw_straight.reverse()


    # ====Search Path with RRT====
    obstacleList = obstacles

    # Set Initial parameters
    start = [start_x, start_y, start_yaw]
    goal = [end_x, end_y, end_yaw]

    rrt = rrt_star.RRT(start, goal, randArea=[0.0, lot_width], obstacleList=obstacleList,
    maxIter=maxIter, curvature=curvature, radius_graph_refinement=radius_graph_refinement)
    path = rrt.Planning(animation=rrt_star_animation)

    # convert
    px, py, pyaw = [], [], []
    for (x, y) in path:
        px.append(x)
        py.append(y)
        pyaw.append(x*0.0) # TODO: change this
    px = list(reversed(px))
    py = list(reversed(py))
    pyaw = list(reversed(pyaw))

    # add path primitives to path
    if primitive_backwards and (detect_space_14 or detect_space_56):
        px = px_backwards + px
        py = py_backwards + py
        pyaw = pyaw_backwards + pyaw

    if straight_at_entrance_:
        px = px_straight_entrance + px
        py = py_straight_entrance + py
        pyaw = pyaw_straight_entrance + pyaw

    if straight_in_parking_space:
        px = px + px_straight
        py = py + py_straight
        pyaw = pyaw + pyaw_straight

    # Draw final path
    rrt.DrawGraph()
    plt.plot(px,py, '-g',lw=3)
    plt.pause(0.001)

    return px, py, pyaw

# collision check
def collision_check(px, py, obstacles, start_number, end_number):
    found_path = True
    crash, out_of_parking_lot = False, False
    for x, y in zip(px, py):
        for obstacle in obstacles:
            if (x <= 0.0 or lot_width <= x or y <= 0.0  or lot_height <= y):
                found_path = False
                out_of_parking_lot = True
            if obstacle[0] == "rectangle":
                if (obstacle[1] < x and x < obstacle[1]+obstacle[3]) and (obstacle[2] < y and y < obstacle[2]+obstacle[4]):
                    found_path = False
                    crash = True
            elif obstacle[0] == "circle":
                if (sqrt((x-obstacle[1])**2 + (y-obstacle[2])**2) < obstacle[3]):
                    found_path = False
                    crash = True
            else:
                exit("SN:ERROR: type {} not known.".format(obstacle[0]))

    if found_path:
        print("\t\tA collision free path from {} to {} was found!".format(start_number,end_number))
    else:
        print("\t\tNo collision free path from {} to {} was found!".format(start_number,end_number))
        if crash:
            print("\t\tThe robot will crash into objects on this path!")
        if out_of_parking_lot:
            print("\t\tThe robot wants to drive outside the parking lot")

    return found_path

# talk
def do_talking(start_x, start_y, start_yaw, start_number, end_x, end_y, end_yaw, end_number):
    print("Path from {} to {}".format(start_number,end_number))
    print("start pose ({}): \n\tx = {}\n\ty = {} \n\ttheta = {}".format(
    start_number, start_x, start_y, degrees(start_yaw) ))
    print("end pose ({}): \n\tx = {}\n\ty = {} \n\ttheta = {}".format(
    end_number, end_x, end_y, degrees(end_yaw) ))
    print("curvature = {}".format(curvature))

# plot
def do_plotting(start_x, start_y, start_yaw, start_number, end_x, end_y, end_yaw, end_number, px, py, objects, obstacles, found_path):
    if close_itself:
        plt.clf()
    fig = plt.figure(1)
    ax = fig.add_subplot(111)
    if found_path:
        plt.plot(px, py,'g-',lw=3)
    else:
        plt.plot(px, py,'m-',lw=3)

    # plt.plot(px, py, label="final course " + "".join(mode))
    dpp.plot_arrow(start_x, start_y, start_yaw,
    0.11*lot_width, 0.06*lot_width, fc="r", ec="r")
    dpp.plot_arrow(end_x, end_y, end_yaw,
    0.11*lot_width, 0.06*lot_width, fc="g", ec="g")
    ax.add_patch( patches.Rectangle( (0.0, 0.0), lot_width, lot_height, fill=False ))
    # plt.legend()
    plt.axis("equal")
    plt.xlim([-visual_boundairy,lot_height+visual_boundairy])
    plt.ylim([-visual_boundairy,lot_width+visual_boundairy])

    # background
    ax.add_patch( patches.Rectangle( (0.0, 0.0), lot_width, lot_height, fc=(0.3,0.3,0.3)))

    # obstacles
    for obstacle in obstacles:
        if obstacle[0] == "rectangle":
            ax.add_patch( patches.Rectangle( (obstacle[1], obstacle[2]),
            obstacle[3], obstacle[4], fc="m", ec="m", hatch='x',lw=0.0))
        if obstacle[0] == "circle":
            ax.add_patch( patches.Circle( (obstacle[1], obstacle[2]),
            obstacle[3], fc="m", ec="m", hatch='x',lw=0.0))

    # boundairies
    r = 1.1*radius_robot
    ax.add_patch( patches.Rectangle( (0.0-r, 0.0-r), r, lot_height+2.0*r, fc="w", ec="w"))
    ax.add_patch( patches.Rectangle( (0.0-r, 0.0-r), lot_height+2.0*r, r, fc="w", ec="w"))
    ax.add_patch( patches.Rectangle( (0.0-r, lot_height), lot_width+2.0*r, lot_height, fc="w", ec="w"))
    ax.add_patch( patches.Rectangle( (lot_width, 0.0-r), r, lot_height+2.0*r, fc="w", ec="w"))


    for obj in objects:
        if obj[5]:
            ax.add_patch( patches.Rectangle( (obj[0], obj[1]), obj[2], obj[3], fc=obj[4]))
        else:
            ax.add_patch( patches.Rectangle( (obj[0], obj[1]), obj[2], obj[3], fc=obj[4], ec="m", hatch='x'))
    ax.add_patch( patches.Rectangle( (0.0, 0.0), lot_width, lot_height, fc=(0.3,0.3,0.3),fill=False))

    # save figure as background
    pickle.dump(ax, file('images/background.pickle', 'w'))

    # if close_itself:
    #     plt.draw()
    #     plt.pause(pause_per_path)
    # else:
    #     plt.show()

    if save_figures:
        dic = {True:'driveable', False:'collision'}
        plt.savefig('images/path_{}_{}_{}.pdf'.format(start_number,end_number,dic[found_path]))


        # if save_figures:
        #     ax = pickle.load(file('images/RRT_star.pickle'))
        #     plt.savefig('images/path_{}_{}_pathes.pdf'.format(start_number,end_number))





def path_planning(start_number=None, end_number=None):
    """
    Problem definition and heuristics
    """
    start_x, start_y, start_yaw, start_number, end_x, end_y, end_yaw, end_number = initialize(start_number, end_number)
    objects = define_objects()
    obstacles = define_obstacles(objects)

    """
    Stage 1: Dubins path
    """
    print('\n\tStage 1: Dubins')

    px, py, pyaw = dubins_path_planning(start_x, start_y, start_yaw, end_x, end_y, end_yaw)
    found_path = collision_check(px, py, obstacles, start_number, end_number)

    # show results
    if ploting:
        do_plotting(start_x, start_y, start_yaw, start_number, end_x, end_y, end_yaw, end_number, px, py, objects, obstacles, found_path)

    if found_path:
        if close_itself:
            plt.pause(pause_per_path)
        else:
            plt.show()
        return
    else:
        plt.pause(0.001)

    """
    Stage 2: RRT*
    """
    print('\n\tStage 2: RRT*')

    px, py, pyaw = RRT_star_path_planning(start_x, start_y, start_yaw, end_x, end_y, end_yaw, obstacles)
    found_path = collision_check(px, py, obstacles, start_number, end_number)

    # show results
    if ploting:
        print('')
        if save_figures:
            dic = {True:'driveable', False:'collision'}
            plt.savefig('images/path_{}_{}_{}.pdf'.format(start_number,end_number,dic[found_path]))
        if close_itself:
            plt.pause(pause_per_path)
        else:
            plt.show()
        # ax = pickle.load(file('images/rrtstar.pickle'))
        # do_plotting(start_x, start_y, start_yaw, start_number, end_x, end_y, end_yaw, end_number, px, py, objects, obstacles, found_path)

        if save_figures:
            ax = pickle.load(file('images/RRT_star.pickle'))
            plt.plot(px, py,'g-',lw=3)
            plt.savefig('images/path_{}_{}_pathes.pdf'.format(start_number,end_number))




"""
main file
"""
if __name__ == '__main__':
    argv = sys.argv[1:]

    # terminal launch
    if len(argv) == 2:
        print("Planning a path from {} to {}: ".format(int(argv[0]),int(argv[1])))
        path_planning(int(argv[0]),int(argv[1]))

    # file launch
    else:
        # path calculation
        init()
        if choose_random_parking_space_combination:
            path_planning()
        else:
            # start_numbers = [0,0,0,0,0,0,1,2,3,4,5,6]
            # end_numbers = [1,2,3,4,5,6,7,7,7,7,7,7]
            start_numbers = [0]
            end_numbers = [4]
            for start_number, end_number in zip(start_numbers, end_numbers):
                print("Planning a path from {} to {}: ".format(start_number, end_number))
                path_planning(start_number, end_number)
                print("\n")
