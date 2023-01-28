import maya.cmds as cmds
import maya.mel as mel
import math as math

def create_centered_loc():
    sel = cmds.ls(selection=True)
    # check if the selection has components
    if any('.' in s for s in sel):
        name = sel[0]
        if '.' in name:
            name = name.split('.')[0]

        # create a cluster and return the handle
        cls = cmds.cluster(sel)[1]
        loc = cmds.spaceLocator(name=name + '_LOC')[0]

        # move loc to cluster and delete cluster
        cmds.delete(cmds.parentConstraint(cls, loc), cls)

    # otherwise use transform with a_to_b
    else:
        for s in sel:
            loc = cmds.spaceLocator(name=s + '_LOC')[0]
            a_to_b(is_trans=True, is_rot=True, sel=[loc, s])

# A function to move the selected objects to the last selected object in the selection list
def a_to_b(sel=None, trans=True, rot=True, sca=False, freeze=False, dHist=False):
    if not sel:
        sel = cmds.ls(selection=True)
    for s in sel[:-1]:
        cmds.matchTransform(s, sel[-1], pos=trans, rot=rot, scl=sca)
        if freeze:
            cmds.makeIdentity(s, apply=True, t=True, r=True, s=True, n=False)
        if dHist:
            cmds.delete(s, ch=True)

def distance_between(node_a=None, node_b=None):
    if not node_a or not node_b:
        cmds.error('A selection of at least 2 objects/nodes in space must exist to use this function')
        
    point_a = cmds.xform(node_a, query=True, worldSpace=True, rotatePivot=True)
    point_b = cmds.xform(node_b, query=True, worldSpace=True, rotatePivot=True)
        
    dist = math.sqrt(sum([pow((b-a), 2) for b, a in zip(point_b, point_a)]))
    
    return dist

def joint_on_curve(sel=None, front_axis='X', up_axis='Z', name=None):

    # Confirm there is a selection
    if not sel:
        sel = cmds.ls(selection=True)

    if len(sel) != 1:
        cmds.confirmDialog(title='Error', message='You must select only 1 curve', button=['OK'], defaultButton = 'OK')
        cmds.error('One curve must be selected to continue')
    else:
        # Prompt a window to set the number of bones

        prompt = cmds.promptDialog(title = 'Joint on Curve', message = 'Number of joints (at least 2)', button=['OK', 'Cancel'],
                                    defaultButton = 'OK', dismissString = 'Cancel')
        if prompt == 'OK':
            chain = cmds.promptDialog(query=True, text=True)
        elif prompt == 'Cancel':
            chain = '0'
    
        if chain <= '1':
            cmds.error('Operation cancelled')
        else:
            chain = int(chain)

    # Create the Locator as a guide
    guideLoc = cmds.spaceLocator(name = 'guide_LOC')

    # Create a motion path
    motionPath = cmds.pathAnimation(guideLoc, curve = sel[0], followAxis = front_axis, upAxis = up_axis, name='motionPath', fractionMode=True, follow=True, worldUpType='vector', worldUpVector=(0,0,0),
                                    startTimeU= cmds.playbackOptions(query=True, minTime=True), endTimeU = cmds.playbackOptions(query=True, maxTime=True))
    
    # Disconnect the motion path's animation key
    cmds.cutKey('motionPath', clear=True)

    nb_div = chain - float(1)
    len_div = 1/nb_div
    u_value = 0
    
    while u_value <= 1:
        cmds.setAttr('motionPath.uValue', u_value)
        if u_value == 0:
            par = None
            jnt = None
        else:
            par = jnt
        jnt = cmds.joint(par)
        cmds.delete(cmds.pointConstraint(guideLoc, jnt, maintainOffset = False))
        u_value += len_div
    
    u_value = 1
    cmds.setAttr('motionPath.uValue', u_value)
    par = jnt
    jnt = cmds.joint(par)
    cmds.delete(cmds.pointConstraint(guideLoc, jnt, maintainOffset = False))
    cmds.joint('joint1', edit=True, oj='xyz', secondaryAxisOrient='zdown', ch=True, zso=True)
    print(u_value)

    # Orient the joints

def add_ctrl(base_name=None, shape='Square', ctrl_size=1, offset_node=False, forward_axis='X'):
    
    if not base_name and cmds.ls(selection=True):
        base_name = cmds.ls(selection=True)[0]
        ctrl_name = change_base_name(base_name, 'CTRL', replace=True)
    elif base_name:
        ctrl_name = change_base_name(base_name, 'CTRL', replace=True) 
    else:
        ctrl_name = shape + '_CTRL'

    for_axis = limb.define_axis(forward_axis) # Returns a Vector3

    if shape == 'Cube':
        ctrl = cmds.curve(n=ctrl_name, d=1, p=[(0.5,0.5,0.5),(0.5,0.5,-0.5),(-0.5,0.5,-0.5),(-0.5,0.5,0.5),(0.5,0.5,0.5),
                                    (0.5,-0.5,0.5),(-0.5,-0.5,0.5),(-0.5,0.5,0.5),(-0.5,-0.5,0.5),(-0.5,-0.5,-0.5),
                                    (-0.5,0.5,-0.5),(-0.5,-0.5,-0.5),(0.5,-0.5,-0.5),(0.5,0.5,-0.5),(0.5,-0.5,-0.5),
                                    (0.5,-0.5,0.5)])
    elif shape == 'Sphere':
        ctrl = cmds.curve(n=ctrl_name, d=1, p=[(1,0,0), (1,0,0)])
    elif shape == 'Circle':
        ctrl = cmds.circle(name = ctrl_name, normal = for_axis)[0]

    elif shape == 'Square':
        ctrl = cmds.circle(n=ctrl_name, d=1, sections=4, normal = for_axis)[0]
        if forward_axis == 'X':
            cmds.xform(ctrl, rotation = (45,0,0))
        if forward_axis == 'Y':
            cmds.xform(ctrl, rotation = (0,45,0))
        if forward_axis == 'Z':
            cmds.xform(ctrl, rotation = (0,0,45))
        cmds.manipPivot(o=(0,0,0))
    
    elif shape == 'Star':
        ctrl = cmds.curve(n=ctrl_name, d=1, p=[(1,0,0),(-1,0,0),(0,0,0),(0,0,1),(0,0,-1),(0,0,0),(0,1,0),(0,-1,0)])
    else:
        cmds.error('No shape has been defined.')
    
    cmds.setAttr(ctrl + '.scale', ctrl_size, ctrl_size, ctrl_size)
    cmds.makeIdentity(apply=True)
    cmds.delete(ch=1)

    grp = cmds.group(ctrl, name=ctrl.replace('CTRL', 'NPO'))
    if offset_node:
        cmds.group(ctrl, name = ctrl.replace('CTRL', 'OFF'))
    return grp