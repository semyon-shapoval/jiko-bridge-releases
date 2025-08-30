import c4d
import maxon

class JBMaterialImporter:
    def __init__(self):
        pass

    def create_redshift_material(self, doc, asset):
        '''
        Documentation for c4d modules
        Graph Node
        https://developers.maxon.net/docs/py/2023_2/modules/maxon_generated/frameworks/graph/datatype/maxon.GraphNode.html

        Graph Interface
        https://developers.maxon.net/docs/py/2023_2/modules/maxon_generated/frameworks/graph/interface/maxon.GraphModelInterface.html
        '''

        RS_ID = "com.redshift3d.redshift4c4d"
        REDSHIFT_NODESPACE_ID = f"{RS_ID}.class.nodespace"
        RS_CORE_ID = f"{RS_ID}.nodes.core"
        RS_OUTPUT_ID = f"{RS_ID}.node.output"

        RS_MATERIAL_ID = f"{RS_CORE_ID}.material"
        RS_TEX_ID = f"{RS_CORE_ID}.texturesampler"
        RS_BUMPMAP_ID = f"{RS_CORE_ID}.bumpmap"
        RS_DISPLACEMENT_ID = f"{RS_CORE_ID}.displacement"

        NODE_NAME_ID = "net.maxon.node.base.name"

        material = c4d.BaseMaterial(c4d.Mmaterial)
        material.SetName(asset.asset_name)

        nodes_material = material.GetNodeMaterialReference()
        nodes_material.AddGraph(REDSHIFT_NODESPACE_ID)
        rs_graph = nodes_material.GetGraph(REDSHIFT_NODESPACE_ID)


        channels = asset.get_textures()

        with rs_graph.BeginTransaction() as transaction:
            rs_material = None
            rs_output = None
            for child in rs_graph.GetRoot().GetChildren():
                if child.IsInner():
                    name = child.GetValue(NODE_NAME_ID)
                    if name == "RS Material":
                        rs_material = child
                    if name == "Output":
                        rs_output = child

            if not rs_material:
                rs_material = rs_graph.AddChild("", RS_MATERIAL_ID)
            if not rs_output:
                rs_output = rs_graph.AddChild("", RS_OUTPUT_ID)

            def create_texture_node(channel):
                texture_path = channels.get(channel, "")
                node = rs_graph.AddChild("",  RS_TEX_ID)
                node.SetValue(NODE_NAME_ID, maxon.String(channel))

                value = maxon.Data(maxon.Url(f"file:///{texture_path}"))

                id = maxon.InternedId(f"{RS_TEX_ID}.color_multiplier")
                node.SetValue(id, value)

                out_node = node.GetOutputs().GetChildren()[0]

                return node, out_node
            
            for channel in channels:
                if channel == "basecolor":
                    node, out_node = create_texture_node(channel)
                    out_node.Connect(
                        rs_material.GetInputs().FindChild(
                            maxon.InternedId(f"{RS_MATERIAL_ID}.diffuse_color")
                        )
                    )

                elif channel == "normal":
                    node, out_node = create_texture_node(channel)
                    bump_node = rs_graph.AddChild("", RS_BUMPMAP_ID)
                    out_node.Connect(
                        bump_node.GetInputs().GetChildren()[0]
                    )
                    out_bump = bump_node.GetOutputs().GetChildren()[0]
                    out_bump.Connect(
                        rs_material.GetInputs().FindChild(
                            maxon.InternedId(f"{RS_MATERIAL_ID}.bump_input")
                        )
                    )
                elif channel == "roughness":
                    node, out_node = create_texture_node(channel)
                    out_node.Connect(
                        rs_material.GetInputs().FindChild(
                            maxon.InternedId(f"{RS_MATERIAL_ID}.refl_roughness")
                        )
                    )

                elif channel == "height":
                    node, out_node = create_texture_node(channel)
                    displacement_node = rs_graph.AddChild("", RS_DISPLACEMENT_ID)
                    out_node.Connect(
                        displacement_node.GetInputs().FindChild(
                            maxon.InternedId(f"{RS_DISPLACEMENT_ID}.texmap")
                        )
                    )
                    out_displacement = displacement_node.GetOutputs().GetChildren()[0]
                    out_displacement.Connect(
                        rs_output.GetInputs().FindChild(
                            maxon.InternedId(f"{RS_OUTPUT_ID}.displacement")
                        )
                    )
                elif channel == "opacity":
                    node, out_node = create_texture_node(channel)
                elif channel == "emissive":
                    node, out_node = create_texture_node(channel)
                    out_node.Connect(
                        rs_material.GetInputs().FindChild(
                            maxon.InternedId(f"{RS_MATERIAL_ID}.emissive_color")
                        )
                    )
                elif channel == "refraction":
                    node = create_texture_node(channel)
                    out_node.Connect(
                        rs_material.GetInputs().FindChild(
                            maxon.InternedId(f"{RS_MATERIAL_ID}.refr_weight")
                        )
                    )
                elif channel == "metallic":
                    node, out_node = create_texture_node(channel)
                    out_node.Connect(
                        rs_material.GetInputs().FindChild(
                            maxon.InternedId(f"{RS_MATERIAL_ID}.refl_metalness")
                        )
                    )
                elif channel == "ao":
                    node = create_texture_node(channel)

            transaction.Commit()

        doc.InsertMaterial(material)

    def create_arnold_material(self, doc, asset):
        from arnold.material import ArnoldNodeMaterial, ArnoldMaterialTransaction

        channels = asset.get_textures()

        arnoldMaterial = ArnoldNodeMaterial.Create(asset.asset_name)

        def create_texture_node(channel):
            texture_path = channels.get(channel, "")
            shader = arnoldMaterial.AddShader("image", maxon.String(channel))
            arnoldMaterial.SetShaderValue(shader, "filename", texture_path)
            return shader

        with ArnoldMaterialTransaction(arnoldMaterial) as transaction:

            standard_surface = arnoldMaterial.AddShader("standard_surface", "standard_surface")
            arnoldMaterial.AddRootConnection(standard_surface, None, "shader")

            correct_node = arnoldMaterial.AddShader("color_correct", "color_correct")
            arnoldMaterial.AddConnection(correct_node, None, standard_surface, "base_color")

            for channel in channels.keys():
                if channel == "basecolor":
                    node = create_texture_node(channel)
                    arnoldMaterial.AddConnection(node, None, correct_node, "input")
                elif channel == "normal":
                    node = create_texture_node(channel)
                    arnoldMaterial.AddConnection(node, None, standard_surface, "normal")
                elif channel == "roughness":
                    node = create_texture_node(channel)
                    arnoldMaterial.AddConnection(node, None, standard_surface, "specular_roughness")
                elif channel == "height":
                    node = create_texture_node(channel)
                    displacement = arnoldMaterial.AddShader("displacement", "displacement")

                    arnoldMaterial.AddRootConnection(displacement, None, "displacement")
                    arnoldMaterial.AddConnection(node, None, displacement, "normal_displacement_input")

                elif channel == "opacity":
                    node = create_texture_node(channel)
                    arnoldMaterial.AddConnection(node, None, standard_surface, "opacity")

                elif channel == "emissive":
                    node = create_texture_node(channel)
                    arnoldMaterial.SetShaderValue(standard_surface, "emissive", 1.0)
                    arnoldMaterial.AddConnection(node, None, standard_surface, "emissive_color")
                elif channel == "refraction":
                    node = create_texture_node(channel)
                    arnoldMaterial.SetShaderValue(standard_surface, "transmission", 1.0)
                    arnoldMaterial.AddConnection(node, None, standard_surface, "transmission_color")
                elif channel == "metallic":
                    node = create_texture_node(channel)
                    arnoldMaterial.AddConnection(node, None, standard_surface, "metalness")
                elif channel == "ao":
                    node = create_texture_node(channel)
                    arnoldMaterial.AddConnection(node, None, correct_node, "multiply")
                else:
                    print(f"Unknown channel: {channel}")

        doc.InsertMaterial(arnoldMaterial.material)

    def create_standard_material(self, doc, asset):
        """Create a standard material from the asset"""
        material = c4d.BaseMaterial(c4d.Mmaterial)
        material.SetName(asset.asset_name)
        material.RemoveReflectionAllLayers()

        doc.InsertMaterial(material)

        channels = asset.get_textures()

        def load_bitmap(channel_name):
            bmp = c4d.BaseShader(c4d.Xbitmap)
            bmp[c4d.BITMAPSHADER_FILENAME] = channels.get(channel_name, "")
            material.InsertShader(bmp)
            return bmp

        def assign_channel_to_material(channel_use_const, channel_shader_const, channel_name):
            try:
                bmp = load_bitmap(channel_name)
                material[channel_use_const] = True if channel_use_const else False
                material[channel_shader_const] = bmp
            except Exception as e:
                print(f"Error assigning {channel_name}: {e}")

        for channel_name in channels.keys():
            if channel_name == "basecolor":
                assign_channel_to_material(
                    c4d.MATERIAL_USE_COLOR,
                    c4d.MATERIAL_COLOR_SHADER,
                    channel_name
                )
            elif channel_name == "normal":
                assign_channel_to_material(
                    c4d.MATERIAL_USE_NORMAL,
                    c4d.MATERIAL_NORMAL_SHADER,
                    channel_name
                )
            elif channel_name == "emissive":
                assign_channel_to_material(
                    c4d.MATERIAL_USE_LUMINANCE,
                    c4d.MATERIAL_LUMINANCE_SHADER,
                    channel_name
                )
            elif channel_name == "opacity":
                assign_channel_to_material(
                    c4d.MATERIAL_USE_ALPHA,
                    c4d.MATERIAL_ALPHA_SHADER,
                    channel_name
                )
            elif channel_name == "refraction":
                assign_channel_to_material(
                    c4d.MATERIAL_USE_TRANSPARENCY,
                    c4d.MATERIAL_TRANSPARENCY_SHADER,
                    channel_name
                )
            elif channel_name == "height":
                assign_channel_to_material(
                    c4d.MATERIAL_USE_DISPLACEMENT,
                    c4d.MATERIAL_DISPLACEMENT_SHADER,
                    channel_name
                )
            elif channel_name == "opacity":
                assign_channel_to_material(
                    c4d.MATERIAL_USE_ALPHA,
                    c4d.MATERIAL_ALPHA_SHADER,
                    channel_name
                )
            elif channel_name == "roughness":
                bmp = load_bitmap(channel_name)
                layer = material.AddReflectionLayer()
                layer.SetName(channel_name)
                data_id = layer.GetDataID()

                material.SetParameter(data_id | c4d.REFLECTION_LAYER_TRANS_TEXTURE,
                    bmp, c4d.DESCFLAGS_SET_0)
                
            elif channel_name == "metallic":
                bmp = load_bitmap(channel_name)
                layer = material.AddReflectionLayer()
                layer.SetName(channel_name)
                data_id = layer.GetDataID()
                material.SetParameter(data_id | c4d.REFLECTION_LAYER_TRANS_TEXTURE,
                    bmp, c4d.DESCFLAGS_SET_0)

            elif channel_name == "ao":
                assign_channel_to_material(
                    c4d.MATERIAL_USE_DIFFUSION,
                    c4d.MATERIAL_DIFFUSION_SHADER,
                    channel_name
                )
            else:
                print(f"Unknown texture: {channel_name}")

        return material

    def import_material(self, asset):
        """Import Material from asset"""
        doc = c4d.documents.GetActiveDocument()
        render_id = doc.GetActiveRenderData()[c4d.RDATA_RENDERENGINE]

        if render_id == 1036219:
            self.create_redshift_material(doc, asset)
        elif render_id == 1029988:
            self.create_arnold_material(doc, asset)
        else:
            self.create_standard_material(doc, asset)