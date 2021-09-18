import maya.cmds as cmds
import cedUtils as cedU
reload(cedU)

def create_limb(joint_list=[], fkChain=True, ikChain=True, mirror=True, forward_axis='X', up_axis='Y', stretch=False):
    
    if joint_list == []:
        joint_list = cmds.ls(selection=True)
    
    # Find the joints that will use Ik and Fk guides
    if len(joint_list) !=3:
        cmds.error('To execute this function, there must be a selection of 3 joints')

    # Create the Ik and Fk chains for the joints in the list
    create_chain(joint_list, fkChain, ikChain, mirror)
    sel = cmds.ls('*IK_GRP*')
    sel.append('*FK_GRP*')
    cmds.group(sel, name='C_arm_FKIK_JNT_GRP')
    
    # Add ctrls for the Fk chain
    if cmds.ls('*FK*', type='joint'):
        FK_joints = cmds.ls('*FK*', type='joint')
    if cmds.ls('*IK*', type='joint'):
        IK_joints = cmds.ls('*IK*', type='joint')
    else:
        cmds.error('There is no valid IK and/or FK chains selected')
    
    # FK ctrls
    fk_list = ['_shoulder_', '_elbow_', '_wrist_']

    for j in FK_joints:
        grp = add_ctrl(j, shape='Circle', ctrl_size=3) # Returns NPO group
        cedU.a_to_b(sel=[grp, j], freeze=False)
        cmds.connectAttr(grp.replace('NPO', 'CTRL') + '.rotate', j + '.rotate')
    
    for s in 'LR':
        cmds.parent(s + fk_list[1] + 'FK_NPO', s + fk_list[0] + 'FK_CTRL')
        cmds.parent(s + fk_list[2] + 'FK_NPO', s + fk_list[1] + 'FK_CTRL')
    grp = cmds.group('*shoulder_FK_NPO*', name='C_arm_FK_CTRL_GRP')
    # cmds.addAttr(grp, attributeType='float', minValue=0, maxValue=1, longName='IKFK_Switch', keyable=True)

    # IK ctrls
    ik_list = ['L_wrist_IK_JNT', 'R_wrist_IK_JNT']
    for j in ik_list:
        ctrl = add_ctrl(j, 'Cube', 3)
        cedU.a_to_b([ctrl, j])

    # IK Handle
    ik_jnt = ['_shoulder_', '_wrist_']
    ikHdl_list = []
    for side in 'LR':
        hdl = cmds.ikHandle(name = side + '_arm_IKH', startJoint=side + ik_jnt[0] + 'IK_JNT', endEffector=side+ ik_jnt[1] + 'IK_JNT')[0]
        cmds.parent(hdl, side + '_wrist_IK_CTRL')
        cmds.orientConstraint(side + '_wrist_IK_CTRL', side + '_wrist_IK_JNT', name = side + '_wrist_IK_ORC')
        ikHdl_list.append(hdl)

    # Create Pole Vectors
    L_IK = []
    R_IK = []
    for j in IK_joints:
        left = j.rfind('L_')
        if left == 0:
            L_IK.append(j)
        else:
            R_IK.append(j)
    for side in 'LR':
        if side == 'L':
            pv_ctrl = create_PV(L_IK, side + '_arm_IK_PV_CTRL')
            cmds.poleVectorConstraint(pv_ctrl, ikHdl_list[0], name=side + '_arm_IK_PVC')
            cmds.parent(pv_ctrl[0].replace('CTRL', 'NPO'), side + '_wrist_IK_NPO')
            
        else:
            pv_ctrl = create_PV(R_IK, side + '_arm_IK_PV_CTRL')
            cmds.poleVectorConstraint(pv_ctrl, ikHdl_list[1], name=side + '_arm_IK_PVC')
            cmds.parent(pv_ctrl[0].replace('CTRL', 'NPO'), side + '_wrist_IK_NPO')

    # Make groups to clean this up in the ouliner
    cmds.group('*wrist_IK_NPO', name='C_arm_IK_CTRL_GRP')
    cmds.group('*chest_JNT', name='C_BIND_JNT_GRP')
    cmds.group('*JNT_GRP', name='JNT_GRP')
    cmds.group('*CTRL_GRP', name='CTRL_GRP')
    cmds.group('JNT_GRP', 'CTRL_GRP', 'GEO_GRP', name='ARM_GRP')

    # Add a switch for the IK and FK chains

    cmds.addAttr('CTRL_GRP', longName='IKFK_Switch', keyable=True, minValue=0, maxValue=1, attributeType='float')

    rvrs_node = cmds.createNode('reverse', name= 'arm_FKIK_rvrs_node')
    cmds.connectAttr('CTRL_GRP.IKFK_Switch', rvrs_node + '.inputX')
    for side in 'LR':
        for jnt in ['shoulder', 'elbow', 'wrist']:
            cmds.connectAttr('CTRL_GRP.IKFK_Switch', side + '_' + jnt + '_JNT_ORC.' + side + '_' + jnt + '_IK_JNTW0')        
            cmds.connectAttr(rvrs_node + '.outputX', side + '_' + jnt + '_JNT_ORC.' + side + '_' + jnt + '_FK_JNTW1')
        cmds.connectAttr('CTRL_GRP.IKFK_Switch', side + '_wrist_IK_NPO.visibility')
        cmds.connectAttr(rvrs_node + '.outputX', side + '_shoulder_FK_CTRL.visibility')

# Define a method to change or add a suffix to the base name 
def change_base_name(base_name=None, suffix=None, replace=False):

    if not base_name:
        base_name = cmds.ls(selection=True)[0]

    if not suffix or base_name != base_name:
        cmds.error('You must indicate what name to change and/or the suffix to add.')
    
    name_comp = base_name.split('_')
    if len(name_comp) <= 2:
        cmds.error('The name must have more than 2 subnames that must be seperated by "_"')
    new_name = ''

    # Add the suffix at the end of the base name
    if not replace:
        new_name = str(base_name) + '_' + str(suffix)
    else:
        name_comp.remove(name_comp[-1])
        name_comp.append(suffix)

        for i in range(len(name_comp)):
            if i == 0:
                new_name += name_comp[i]
            else:
                new_name += '_' + name_comp[i]
    return new_name

def create_PV(sel=None, base_name=None):
    if not sel:
        sel = cmds.ls(selection=True)
    if len(sel) != 3:
        cmds.error('A selection of 3 joints must be made')
    
    if not base_name:
        loc_name = 'arm_IK_PV_CTRL'
    else:
        loc_name = base_name
    loc = add_ctrl(loc_name, shape='Star',ctrl_size=2, forward_axis='Z')

    # Trouver les distances entre les joint pour ajuster le parentConstraint
    distUp = cedU.distance_between(sel[0], sel[1])
    distDown = cedU.distance_between(sel[0], sel[2])


    constr = cmds.parentConstraint(sel, loc, name=loc + '_PAC')

    cmds.setAttr(constr[0] + '.' + sel[1] + 'W1', distDown)
    cmds.setAttr(constr[0] + '.' + sel[2] + 'W2', distUp)
    cmds.delete(constr)

    cmds.delete(cmds.aimConstraint(sel[0], loc, offset = (10,0,0)))
    cmds.move(10,0,0, loc, relative=True, objectSpace=True, worldSpaceDistance=True)
    cmds.setAttr(loc + '.rotate', 0,0,0)

    pv_ctrl = cmds.ls(loc.replace('NPO', 'CTRL'))
    return pv_ctrl

def bind_jnts_constraint(bind_jnt=None, par=None, parentConstraint=False, orientConstraint=True, pointConstraint=False, name=None):
    if not bind_jnt or not par:
        sel = cmds.ls(selection=True)
        if sel == []:
            cmds.error('There is no joints selected')
        else:
            bind_jnt = sel[-1]
            par = sel[:-2]

    if parentConstraint:
        cnst = cmds.parentConstraint(par, bind_jnt, name=name)

    elif pointConstraint and not orientConstraint:
        cnst = cmds.pointConstraint(par, bind_jnt, name=name)

    elif orientConstraint and not pointConstraint:
        cnst = cmds.orientConstraint(par, bind_jnt, name=name)

    elif orientConstraint and pointConstraint:
        cnst = cmds.pointConstraint(par, bind_jnt, name=name)
        cnst2 = cmds.orientConstraint(par, bind_jnt, name=name)
        cnst = [cnst, cnst2]

    else:
        cmds.warning('The constraint could not have been done')

    return cnst, type(cnst)

def create_chain(joint_list=[], fkChain=True, ikChain=True, mirror=True): # Returns a list of list(s)
    
    chain_list = []

    # Look for any selection in the scene
    if joint_list == []:
        joint_list = cmds.ls(selection=True)
    if len(joint_list) != 3:
        cmds.error('A selection of 3 joints must be made to continue. Please make the selection from the base of the joint to the tip')

    joint_lists = [joint_list]

    if mirror:
        mirror_list = []
        side_name = str(joint_list[0][0])
        if side_name == 'L':
            mirror_jnt = 'R'
        elif side_name == 'R':
            mirror_jnt = 'L'
        else:
            cmds.error('The selected joints cannot be mirrored')
        # Add the mirrored joints to the mirror list
        for j in joint_list:
            mirror_list.append(j.replace(side_name, mirror_jnt))
        joint_lists = [joint_list, mirror_list]
    
    # Find what types of chains we want to create
    if not ikChain and fkChain:
        cmds.error('You must select what chains you want to add to your limb joints')
    if ikChain:
        chain_list.append('IK_JNT')
    if fkChain:
        chain_list.append('FK_JNT')

    # Duplicate the mentionned joints as new chains
    for l in joint_lists:
        for c in chain_list:
            for j, jnt in enumerate(l):
                # Split the name of the selected joints, then create the chain name
                chain_name = change_base_name(base_name=jnt, suffix=c, replace=True)

                # Create the joint with the same scale
                par_rad = cmds.joint(jnt, query=True, rad=True)[0]

                chain_jnt = cmds.joint(None, name = chain_name, rad=par_rad)
                
                # Create the list for the a_to_b method
                chain = [chain_jnt]
                chain.append(jnt)

                # Get the position and the rotation of the selected joints
                cedU.a_to_b(sel=chain, freeze=True)

                # Parent the joint to the last chain joint created
                if j == 0:
                    grp = cmds.group(chain_jnt, name=chain_name.replace('JNT', 'GRP'))
                    par_jnt = chain_jnt
                else:
                    cmds.parent(chain_jnt, par_jnt)
                    par_jnt = chain_jnt
    for j in joint_lists:
        for jnt in j:
            bind_jnts_constraint(jnt, [jnt.replace('JNT', 'IK_JNT'), jnt.replace('JNT', 'FK_JNT')], name=jnt + '_ORC')

def add_ctrl(base_name=None, shape='Square', ctrl_size=1, offset_node=False, forward_axis='X'):
    
    if not base_name and cmds.ls(selection=True):
        base_name = cmds.ls(selection=True)[0]
        ctrl_name = change_base_name(base_name, 'CTRL', replace=True)
    elif base_name:
        ctrl_name = change_base_name(base_name, 'CTRL', replace=True) 
    else:
        ctrl_name = shape + '_CTRL'

    for_axis = define_axis(forward_axis) # Returns a Vector3

    if shape == 'Cube':
        ctrl = cmds.curve(n=ctrl_name, d=1, p=[(0.5,0.5,0.5),(0.5,0.5,-0.5),(-0.5,0.5,-0.5),(-0.5,0.5,0.5),(0.5,0.5,0.5),
                                    (0.5,-0.5,0.5),(-0.5,-0.5,0.5),(-0.5,0.5,0.5),(-0.5,-0.5,0.5),(-0.5,-0.5,-0.5),
                                    (-0.5,0.5,-0.5),(-0.5,-0.5,-0.5),(0.5,-0.5,-0.5),(0.5,0.5,-0.5),(0.5,-0.5,-0.5),
                                    (0.5,-0.5,0.5)])
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
    
def create_base_skel():
    mH = float(2) # Model Height
    nb_spine = 7

    C_jnt_list = ['COG', 'spine', 'hips', 'chest', 'neck', 'head', 'headTip']
    C_jnt_pos_list = [mH/2, mH/2 + mH/50, mH/2 - mH/50, (mH/2 + mH/50 + mH/4), (mH/2 + mH/3 + mH/16), (mH/2 + mH/4 + mH/8), mH]
    C_jnt_child_list = [None, C_jnt_list[0], C_jnt_list[0], C_jnt_list[1], C_jnt_list[3], C_jnt_list[4], C_jnt_list[5]]
    print(C_jnt_pos_list)
    L_arm_jnt_list = ['clavicle', 'arm', 'elbow', 'wrist', 'hand']
    L_leg_jnt_list = ['leg', 'knee', 'ankle', 'ball', 'toeTip']
    

    for i in range(len(C_jnt_list)):
        
        if i == 0:
            jnt = cmds.joint(C_jnt_child_list[i], absolute=True, position = (0, C_jnt_pos_list[i], 0), radius = 0.1, name= 'C_' + C_jnt_list[i] + '_JNT')
        else:
            jnt = cmds.joint('C_' + C_jnt_child_list[i] + '_JNT', absolute=True, position = (0, C_jnt_pos_list[i], 0), radius = 0.1, name= 'C_' + C_jnt_list[i] + '_JNT')

def define_axis(axis, is_negative=False): # Axis = XYZ; X=orient direction, Y=secondary orient, Z=up/normal

    if type(axis) == str:
        if is_negative:
            sign_value = -1
        else:
            sign_value = 1
        
        if axis[-1] == 'X':
            vector_axis = (sign_value,0,0)
        if axis[-1] == 'Y':
            vector_axis = (0,sign_value,0)
        if axis[-1] == 'Z':
            vector_axis = (0,0,sign_value)
        return vector_axis

    # if type(axis) == tuple or list:

    else:
        cmds.error('Cannot define a vector out of the argument(s) given.')
