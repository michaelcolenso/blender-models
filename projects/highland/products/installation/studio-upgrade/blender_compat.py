"""Version-aware interactive EEVEE preview and optional compositor glow."""
import bpy


def eevee_preview(scene):
    """Cycles remains the delivered shadow-catcher path; EEVEE uses a matte floor."""
    scene.render.engine = 'BLENDER_EEVEE' if bpy.app.version >= (5,0,0) else 'BLENDER_EEVEE_NEXT'
    scene.eevee.taa_render_samples = 128
    scene.eevee.use_raytracing = True
    scene.eevee.ray_tracing_method = 'SCREEN'
    scene.eevee.fast_gi_method = 'AMBIENT_OCCLUSION_ONLY'
    scene.eevee.shadow_ray_count = 4
    scene.eevee.use_shadow_jitter_viewport = True
    for obj in scene.objects:
        if obj.get('presentation_role') == 'shadow_catcher':
            obj.is_shadow_catcher = False
    scene['eevee_limit'] = 'Interactive matte receiver preview. Exact Cycles shadow-catcher compositing is not reproduced by EEVEE.'


def restrained_glow(scene):
    """Optional: keep the direct material result, with only a small highlight halo."""
    if bpy.app.version >= (5,0,0):
        tree=bpy.data.node_groups.new('Studio subtle glow','CompositorNodeTree')
        tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
        scene.compositing_node_group=tree
        output=tree.nodes.new('NodeGroupOutput')
        glare=tree.nodes.new('CompositorNodeGlare')
        glare.inputs['Type'].default_value='Fog Glow'
        glare.inputs['Quality'].default_value='High'
        glare.inputs['Threshold'].default_value=1.5
        glare.inputs['Strength'].default_value=.04
        glare.inputs['Size'].default_value=.15
    else:
        scene.use_nodes=True
        tree=scene.node_tree
        tree.nodes.clear()
        output=tree.nodes.new('CompositorNodeComposite')
        glare=tree.nodes.new('CompositorNodeGlare')
        glare.glare_type='FOG_GLOW'
        glare.quality='HIGH'
        glare.threshold=1.5
        glare.mix=-.95
        glare.size=7
    render=tree.nodes.new('CompositorNodeRLayers')
    render.scene=scene
    tree.links.new(render.outputs['Image'],glare.inputs['Image'])
    tree.links.new(glare.outputs['Image'],output.inputs['Image'])
    scene.render.use_compositing=True
    return tree
